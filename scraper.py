#!/usr/bin/env python

import scraperwiki
 
import lxml.html
import requests

def get_number_of_pages(starturl):
    """For a given starturl, get the number of pages that is possible to scrape"""
    s = requests.session()
    r1 = s.get(starturl)

    html = r1.text
    #process page one
    root = lxml.html.fromstring(html)

    #pick up the javascript values
    EVENTVALIDATION = root.xpath('//input[@name="__EVENTVALIDATION"]')[0].attrib['value']
    #find the __EVENTVALIDATION value
    VIEWSTATE = root.xpath('//input[@name="__VIEWSTATE"]')[0].attrib['value']
    #find the __VIEWSTATE value
    #  build a dictionary to post to the site with the values we have  collected. The __EVENTARGUMENT can be changed to fetch another result   page (3,4,5 etc.)
    payload = {'__EVENTTARGET': 'ctl00$ContentPlaceHolder3$grwIzvestaji', '__EVENTARGUMENT': 'Page$Last','referer':'http://portal.ujn.gov.rs/Izvestaji.aspx','__EVENTVALIDATION':EVENTVALIDATION,'__VIEWSTATE':VIEWSTATE,'ctl00$txtUser':'','ctl00$txtPass':'','ctl00$ContentPlaceHolder1$txtSearchIzvestaj':'','__VIEWSTATEENCRYPTED':''}

    # post it
    lastPage = s.post(starturl, data=payload)

    html = lastPage.text

    #print html
    
    root = lxml.html.fromstring(html)
    tablefooter = root.xpath('//tr[@class="TableFootSimple left"]')
    spanpage = tablefooter[0].cssselect('span')

    return int(spanpage[0].text)

def request_n_return_page(scrape_session,starturl,EVENTVALIDATION,VIEWSTATE,page):
    """This function, given a session, a starting url and the EVENTVALIDATION and VIEWSTATE tokens, retrieves a given page are return its html"""
    print "Requesting page " + str(page)
    payload = {'__EVENTTARGET': 'ctl00$ContentPlaceHolder3$grwIzvestaji', '__EVENTARGUMENT': 'Page$'+str(page),'referer':'http://portal.ujn.gov.rs/Izvestaji.aspx','__EVENTVALIDATION':EVENTVALIDATION,'__VIEWSTATE':VIEWSTATE,'ctl00$txtUser':'','ctl00$txtPass':'','ctl00$ContentPlaceHolder1$txtSearchIzvestaj':'','__VIEWSTATEENCRYPTED':''}
    return_page = scrape_session.post(starturl, data=payload);

    return return_page.text

def dump_header(html):
    #scraperwiki.sqlite.execute("drop table header_info")

    try:     
        scraperwiki.sqlite.execute("""         
            create table header_info
            (          
            COLUMN00 TEXT,
            COLUMN01 TEXT,
            COLUMN02 TEXT,
            COLUMN03 TEXT,        
            COLUMN04 TEXT,
            COLUMN05 TEXT,
            COLUMN06 TEXT,
            COLUMN07 TEXT,
            COLUMN08 TEXT,
            COLUMN09 TEXT,
            COLUMN10 TEXT,
            COLUMN11 TEXT,
            COLUMN12 TEXT,
            COLUMN13 TEXT,
            COLUMN14 TEXT,
            COLUMN15 TEXT
            )     
        """)
    except:   
        print "Table probably already exists."


    header = []
    real_header = []
    col_number = 0
    table_id = "ctl00_ContentPlaceHolder3_grwIzvestaji"
    root = lxml.html.fromstring(unicode(html))
    table = root.cssselect("table#"+table_id)[0]
    for row in table.cssselect("tr"):
        if( row.get("class") == "HeadTitle") :
            for th in row.cssselect("th"):
                son = th.getchildren()[0];
                gson = son.getchildren()[0];
                ggson = gson.getchildren()[0];
                real_header.append(ggson.text)               
                header.append("COLUMN"+str(col_number).zfill(2))
                col_number = col_number + 1
    
                
    scraperwiki.sqlite.save(header,dict(zip(header,real_header)),table_name="header_info")


def extract_data_n_dump(html,page):
    col_number = 0
    header = []
    record_to_save = []
    table_id = "ctl00_ContentPlaceHolder3_grwIzvestaji"
    root = lxml.html.fromstring(unicode(html))
    table = root.cssselect("table#"+table_id)[0]
    for row in table.cssselect("tr"):
        if( row.get("class") == "HeadTitle") :
            for th in row.cssselect("th"):
                son = th.getchildren()[0];
                gson = son.getchildren()[0];
                ggson = gson.getchildren()[0];
                #header.append(ggson.text)
                #non ascii characters not supported in column name
                header.append("COLUMN"+str(col_number).zfill(2))
                col_number = col_number + 1
            header_primary_key = header
            header.append("page_number")
        else:
            datarow = []
            for td in row.cssselect("td"):
                son = td.getchildren()[0]
                if( not( son.text is None ) ):
                     datarow.append(son.text)
            datarow.append(page)
            if len(header) == len(datarow):
                record_to_save.append(dict(zip(header,datarow)))
    print "Inserting " + str(len(record_to_save)) + " records"
    scraperwiki.sqlite.save([],record_to_save,table_name="contracts")
    root = lxml.html.fromstring(html)
    EVENTVALIDATION = root.xpath('//input[@name="__EVENTVALIDATION"]')[0].attrib['value']
    VIEWSTATE = root.xpath('//input[@name="__VIEWSTATE"]')[0].attrib['value']  
    

def get_validation_data(session_obj,starturl,last_page):
    """This routing saves the EVENTVALIDATION and VIEWSTATE data for retriving each page. It is not necessary to use it as long as nothing wrong happened 
       with the main scraping loop, that corrupted the information necessary to resume the scraping"""
    #get page 1
    r1 = session_obj.get(starturl)
    
    print "The encoding of the page is " + r1.encoding

    html = r1.text

    #print html
    #process page one, to obtain the EVENTVALIDATION and VIEWSTATE for page one, than continue for page 16,31,46,etc etc
    root = lxml.html.fromstring(html)
    EVENTVALIDATION = root.xpath('//input[@name="__EVENTVALIDATION"]')[0].attrib['value']
    VIEWSTATE = root.xpath('//input[@name="__VIEWSTATE"]')[0].attrib['value']  

    #Try to resume from the last obtained validation data
    try:
        res = scraperwiki.sql.select("* FROM VALIDATION_DATA ORDER BY page DESC LIMIT 2");
        last_scraped_validation_page = int(res[0]['page']);
        EVENTVALIDATION = res[1]["EVENTVALIDATION"];
        VIEWSTATE = res[1]["VIEWSTATE"];
    except:
        print "Starting validation data harvesting from the start"
        last_scraped_validation_page = 1;

    header_validation = ["page","EVENTVALIDATION","VIEWSTATE"]
    for i in range(last_scraped_validation_page,last_page,15):
        results = []
        if i == 1:
            new_page_html = html
        else:
            new_page_html = request_n_return_page(session_obj,starturl,EVENTVALIDATION,VIEWSTATE,i)
        results.append(i)
        root = lxml.html.fromstring(new_page_html)
        EVENTVALIDATION = root.xpath('//input[@name="__EVENTVALIDATION"]')[0].attrib['value']
        VIEWSTATE = root.xpath('//input[@name="__VIEWSTATE"]')[0].attrib['value']  
        results.append(EVENTVALIDATION)
        results.append(VIEWSTATE)
        scraperwiki.sqlite.save(["page"],dict(zip(header_validation,results)),table_name="VALIDATION_DATA")
   


def main():
    """Main function of the scraper. Hopefully running this function should start (or resume) the scraping of contracts data"""

    #define the homepage of the table with the contract
    starturl = "http://stariportal.ujn.gov.rs/Izvestaji.aspx"


    #Creating table if the contracts table does not exists
    try:     
        scraperwiki.sqlite.execute("""         
        create table contracts
        (          
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_number INTEGER,
        COLUMN00 TEXT,
        COLUMN01 TEXT,
        COLUMN02 TEXT,
        COLUMN03 TEXT,        
        COLUMN04 TEXT,
        COLUMN05 TEXT,
        COLUMN06 TEXT,
        COLUMN07 TEXT,
        COLUMN08 TEXT,
        COLUMN09 TEXT,
        COLUMN10 TEXT,
        COLUMN11 TEXT,
        COLUMN12 TEXT,
        COLUMN13 TEXT,
        COLUMN14 TEXT,
        COLUMN15 TEXT
        )     
        """)
    except:   
        print "contracts table already existing"

    #Get the total number of pages to scape
    last_page = get_number_of_pages(starturl);

    print "There is a total of " + str(last_page) + " pages to scrape "


    # create a session object
    s = requests.session()
    
    #not necessary as long that the main scraping loop has no problem
    #get_validation_data(s,starturl,last_page);

    #get page 1
    r1 = s.get(starturl)
    
    print "The encoding of the page is " + r1.encoding

    html = r1.text

    #print html
    #process page one, to obtain the EVENTVALIDATION and VIEWSTATE for page one, than continue for page 16,31,46,etc etc
    root = lxml.html.fromstring(html)
    EVENTVALIDATION = root.xpath('//input[@name="__EVENTVALIDATION"]')[0].attrib['value']
    VIEWSTATE = root.xpath('//input[@name="__VIEWSTATE"]')[0].attrib['value']  
    #dump_header(html)

    #disabled because all data is scraped
    #if more data is added to the site please write me


    print scraperwiki.sqlite.get_var('last_page_scraped')
    if( not( scraperwiki.sqlite.get_var('last_page_scraped') is None ) and not( scraperwiki.sqlite.get_var('last_page_scraped') == 1 ) ):
        j = scraperwiki.sqlite.get_var('last_page_scraped')
        EVENTVALIDATION = scraperwiki.sqlite.get_var('EVENTVALIDATION')
        VIEWSTATE = scraperwiki.sqlite.get_var('VIEWSTATE')
    else:
        j = 1

    #print "Requesting page 10516"
    #print request_n_return_page(s,starturl,EVENTVALIDATION,VIEWSTATE,10516)


    for i in range(j,last_page+1):
        if( i == 1 ):
            new_page_html = html
        else:
            new_page_html = request_n_return_page(s,starturl,EVENTVALIDATION,VIEWSTATE,i)

        #do stuff with html
        print "Downloaded page " + str(i) + " of " + str(last_page)
        print "Lenght of page " + str(i) + " : " + str(len(new_page_html))
        extract_data_n_dump(new_page_html,i)
    
        scraperwiki.sqlite.save_var('EVENTVALIDATION',EVENTVALIDATION)
        scraperwiki.sqlite.save_var('VIEWSTATE',VIEWSTATE)
        scraperwiki.sqlite.save_var('last_page_scraped', i+1)
        

        #get new javascript values
        root = lxml.html.fromstring(new_page_html)
        #pick up the javascript values
        EVENTVALIDATION = root.xpath('//input[@name="__EVENTVALIDATION"]')[0].attrib['value']
        VIEWSTATE = root.xpath('//input[@name="__VIEWSTATE"]')[0].attrib['value']



##main code

#scraperwiki.sqlite.save_var('last_page_scraped', 1)
#scraperwiki.sqlite.execute("drop table if exists contracts")

#scraperwiki.sqlite.save_var('last_page_scraped', 10530)

#scraperwiki.sqlite.save_var('EVENTVALIDATION',EVVAL)
#scraperwiki.sqlite.save_var('VIEWSTATE',EVSTA)
#scraperwiki.sqlite.execute("delete from contracts where page_number > 10529")
#scraperwiki.sqlite.execute("delete from sqlite_sequence where seq > 105200")
#scraperwiki.sqlite.execute("insert or replace into sqlite_sequence values (:name, :seq)", {"name":"contracts", "seq":105290})
#scraperwiki.sqlite.commit()

#scraperwiki.sqlite.execute("drop table if exists swdata")


#In the script simply run the main() function, all should be inside there
main();



