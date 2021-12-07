import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

for page_number in range(1, 11):
    url = f'https://tululu.org/l55/{page_number}'
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')
    book_cards = soup.find_all('table', class_='d_book')

    for book_card in book_cards:
        book_id = book_card.find('a')['href']
        book_url = urljoin('https://tululu.org', book_id)
        print(book_url)