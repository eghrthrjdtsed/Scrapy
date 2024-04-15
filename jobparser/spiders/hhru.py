import scrapy
from scrapy.http import HtmlResponse
from jobparser.items import JobparserItem
import re


class HhruSpider(scrapy.Spider):
    name = "hhru"
    allowed_domains = ["hh.ru"]
    start_urls = [
        "https://hh.ru/search/vacancy?text=python&area=53&hhtmFrom=resume_view_history&hhtmFromLabel=vacancy_search_line"
    ]

    def parse(self, response: HtmlResponse):
        '''
        Метод для обработки каждого ответа на запрос веб-страницы.

        :param response: HtmlResponse - объект, содержащий данные ответа на запрос.
        :return: None
        '''
        # Извлечение ссылки на следующую страницу пагинации вакансий
        next_page = response.xpath(".//a[@data-qa='pager-next']/@href").get()
        if next_page:
            # Переход на следующую страницу и вызов этого же метода для обработки
            yield response.follow(next_page, callback=self.parse)

        # Извлечение ссылок на отдельные вакансии на текущей странице
        links = response.xpath(".//span[@data-page-analytics-event='vacancy_search_suitable_item']//@href").getall()

        # Обход ссылок на отдельные вакансии и вызов метода vacancy_parse для их обработки
        for link in links:
            yield response.follow(link, callback=self.vacancy_parse)

    def vacancy_parse(self, response: HtmlResponse):
        '''
        Метод для обработки отдельной страницы вакансии.

        :param response: HtmlResponse - объект, содержащий данные ответа на запрос.
        :return: None
        '''
        # Извлечение названия вакансии
        name = response.xpath("//h1/text()").get()

        # Извлечение текстового представления зарплаты
        salary_text = response.xpath("//div[@data-qa='vacancy-salary']//text()").getall()

        # Получение URL текущей страницы
        url = response.url

        # Обработка информации о зарплате
        salary = self.process_salary(salary_text)

        # Возврат элемента JobparserItem с извлеченными данными
        yield JobparserItem(name=name, salary=salary, url=url)

    def process_salary(self, salary_text):
        '''
        Метод для обработки текстового представления зарплаты.

        :param salary_text: str - текстовое представление зарплаты.
        :return: tuple/float or None - кортеж из двух элементов (нижняя и верхняя граница зарплаты),
                                        одно число (если указана только одна граница) или None, если информация о зарплате не найдена.
        '''
        # Если текст зарплаты отсутствует, возвращаем None
        if not salary_text:
            return None

        # Объединяем строки текста зарплаты в одну строку
        salary_text = ' '.join(salary_text)

        # Поиск информации о зарплате в тексте
        match = re.search(r'(?:от\s*)?(\d+(?:\s+\d+)*(?:,\d+)?)\s*(?:до\s*)?(\d+(?:\s+\d+)*(?:,\d+)?)?\s*₽\s*(.*)',
                          salary_text.replace('\xa0', ' '))

        # Если информация о зарплате найдена
        if match:
            # Извлечение нижней и верхней границ зарплаты (если они указаны)
            lower_bound = float(match.group(1).replace(' ', '').replace(',', '.')) if match.group(1) else None
            upper_bound = float(match.group(2).replace(' ', '').replace(',', '.')) if match.group(2) else None

            # Возврат кортежа из двух границ зарплаты, если указаны обе границы
            if upper_bound:
                return lower_bound, upper_bound
            # Возврат одной границы зарплаты, если указана только нижняя граница
            elif lower_bound:
                return lower_bound

        # Если информация о зарплате не найдена, возвращаем None
        return None
