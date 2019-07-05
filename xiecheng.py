import asyncio
import csv
import re

import requests
from pyppeteer import launch, errors
from queue import Queue

headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.90 Safari/537.36",
}

city_url = 'https://hotels.ctrip.com/Domestic/Tool/AjaxGetCitySuggestion.aspx'
res = requests.get(city_url, headers=headers)




def screen_size():
    """使用tkinter获取屏幕大小"""
    import tkinter
    tk = tkinter.Tk()
    width = tk.winfo_screenwidth()
    height = tk.winfo_screenheight()
    tk.quit()
    return width, height


class XiuChenHotel(object):
    @staticmethod
    def _re_list(cite_list: str) -> list:
        cite_list = re.findall("data:(.*?),", cite_list)
        city_code = []
        for city in cite_list:
            city_info = {}
            e_name, c_name, c_num = city.split('|')
            city_info[c_name] = (e_name + c_num).strip("\"")
            city_code.append(city_info)
        return city_code

    @staticmethod
    def _city_number() -> list:
        city_li = ['ABCD', 'EFGH', 'JKLM', 'TUVWX', 'TUVWX', 'NOPQRS', 'YZ']
        city_list = []
        for city_num in city_li:
            num = re.search(r"{}:\[(.*?)]".format(city_num), res.text).group(1)
            city_list.extend(XiuChenHotel._re_list(num))
        return city_list

    @staticmethod
    def all_hotel() -> list:
        city_list = []
        for city in XiuChenHotel._city_number():
            v = ''.join([v for v in city.values()])
            url = 'https://hotels.ctrip.com/hotel/{}#ctm_ref=hod_hp_sb_lst'.format(v)
            city_list.append(url)
        return city_list

hotel_id = 0
def write_csv(row_list:list):
    path = 'hotel.csv'
    with open(path,'w+',encoding='utf_8_sig', newline='') as f:
        csv_write = csv.writer(f)
        data_row = ['id','name','star', 'price', 'addr']
        csv_write.writerow(data_row)
        for row in row_list:
            global hotel_id
            hotel_id+=1
            row.insert(0,hotel_id)
            csv_write.writerow(row)






async def go_hotel(url: str):
    browser = await launch(
        {'headless': False, 'args': ['--no-sandbox', '--disable-infobars'], 'ignoreHTTPSErrors': True,
         'dumpio': False, })

    width, height = screen_size()

    context = await browser.createIncognitoBrowserContext()
    page = await context.newPage()
    await page.setUserAgent(
        "Mozilla/5.0 (Windows NT 6.2; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36")
    await page.setViewport({'width': width, 'height': height})
    try:
        await page.goto(url, {'timeout': 0})
    except Exception as e:
        print('网络请求超时')

    # async def wait_for(select):
    #     if "#" not in select[0]:
    #         while not await page.xpath(select):
    #             pass
    #     else:
    #         while not await page.querySelector(select):
    #             pass

    async def wait_click(select):
        await page.waitFor(select)
        await page.click(select)

    _day = '#txtCheckIn'
    people = "#J_RoomGuestInfoTxt"
    add_butn = "#J_AdultCount .number_plus"
    add_entry = "#J_RoomGuestInfoBtnOK"
    four_star = '#star-4'
    five_star = "#star-5"
    price = "#priceRange>input:nth-child(1)"
    search = "#btn_range"
    await wait_click(_day)
    await page.keyboard.press("Home")
    await page.keyboard.down("Shift")
    await page.keyboard.press("End")
    await page.keyboard.press("Delete")
    await page.keyboard.up("Shift")
    await page.type(_day, '2019-07-10')

    await wait_click(people)
    await wait_click(add_butn)
    await wait_click(add_entry)
    await wait_click(four_star)
    await wait_click(five_star)
    await page.waitForSelector(".searchresult_list_load", hidden=True)
    await page.type(price, '700')

    await wait_click(search)
    await page.waitForSelector(".searchresult_list_load", hidden=True)
    # await page.evaluate('window.scrollBy(0, document.body.scrollHeight)')

    # 每页的酒店数不同
    _page_num_xpath = '//div[@id="hotel_list"]/div[last()-1]//span[@class="hotel_num"]'
    await page.waitForXPath(_page_num_xpath)
    _page_num = await page.xpath(_page_num_xpath)
    page_num = await (await _page_num[0].getProperty("textContent")).jsonValue()


    hotel_list_xpath = '//div[@id="hotel_list"]/div[position()<{}]'.format(page_num)
    await page.waitForXPath(hotel_list_xpath)
    hotel_list = await page.xpath(hotel_list_xpath)

    async def get_hotel():
        hotel_infos = list()
        for hotel in hotel_list:
            _title = await hotel.xpath('.//a')
            title = await (await _title[0].getProperty("title")).jsonValue()
            _level = await hotel.xpath('.//a[@class="hotel_judge"]')
            level = await (await _level[0].getProperty("title")).jsonValue()
            star = re.search(r'\d\.\d分', level).group()
            _addr = await hotel.xpath('.//p[@class="hotel_item_htladdress"]/text()')
            addr = ''.join([await (await i.getProperty('textContent')).jsonValue() for i in _addr])
            addr = re.sub(r'[【】\s。]', '', addr)
            _price = await hotel.xpath('.//span[@class="J_price_lowList"]')
            price = await (await _price[0].getProperty('textContent')).jsonValue()
            hotel_infos.append([title,star,price,addr])
        print(hotel_infos)

    # write_csv(hotel_infos)

    _next_page_select = '#downHerf'
    await page.waitForSelector(_next_page_select)
    next_page_select = await page.querySelector(_next_page_select)
    next_page_class = await (await next_page_select[0].getProperty("class")).jsonValue()
    print(next_page_class)
    if next_page_class == "c_down":
        await page.click(next_page_select)
        await get_hotel()
        print('222')
    print('111')
    await get_hotel()





    await page.close()
    await context.close()
    await browser.close()
    # await page.evaluateOnNewDocument(js1, js2, js3, js4)

async def work(url,sem):
    async with sem:
        print('run a work', url)
        await go_hotel(url)
        print('work over', url)

async def run():
    sem = asyncio.Semaphore(1)
    works = [work(url,sem) for url in XiuChenHotel.all_hotel()]
    await asyncio.wait(works)

    # works = list()
    # for url in XiuChenHotel.all_hotel():
    #     works.append(work(url))

    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(asyncio.wait(works))


if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(run())

    loop = asyncio.get_event_loop()
    url = 'https://hotels.ctrip.com/hotel/Abazhou1838#ctm_ref=hod_hp_sb_lst'
    # for url in XiuChenHotel.all_hotel():
    #     print(url)
    #     loop.run_until_complete(go_hotel(url))
    loop.run_until_complete(go_hotel(url))
