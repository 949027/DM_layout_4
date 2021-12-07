import json
import requests
import re
import os
from urllib.parse import urljoin, urlsplit, unquote
from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
import argparse
from pathlib import Path


def download_image(soup, folder='images/'):
    url_image = urljoin(
        'https://tululu.org',
        soup.select_one('div.bookimage img')['src'],
    )
    response = requests.get(url_image)
    response.raise_for_status()

    url_path_image = urlsplit(url_image)[2]
    filename = unquote(os.path.split(url_path_image)[1])
    path = os.path.join(folder, filename)

    with open(path, 'wb') as file:
        file.write(response.content)


def download_txt(soup, book_id, books_path):
    book_url = "https://tululu.org/txt.php"
    payload = {'id': book_id}

    title_tag = soup.select_one('h1')
    title_text = title_tag.text
    title, _ = title_text.split(sep='::')
    title_book = '{}. {}'.format(
        book_id,
        title.strip(),
    )

    clean_filename = f"{sanitize_filename(title_book)}.txt"
    path = os.path.join(books_path, clean_filename)

    response = requests.get(book_url, params=payload)
    response.raise_for_status()

    with open(path, 'w') as file:
        file.write(response.text)

    return path


def parse_book_description(soup):
    title_tag = soup.select_one('h1')
    title_text = title_tag.text
    title, author = title_text.split(sep='::')

    comment_blocks = soup.select('div.texts')
    genres_blocks = soup.select('span.d_book a')

    genres = [genre.get_text() for genre in genres_blocks]
    comments = [
        comment.select_one('span.black').text for comment in comment_blocks
    ]

    book_description = {
        'title': title.strip(),
        'author': author.strip(),
        'genres': genres,
        'comments': comments
    }
    return book_description


def main():
    book_descriptions = []

    parser = argparse.ArgumentParser(
        description='Программа для скачивания книг с tululu.org'
    )
    parser.add_argument(
        '--start_page',
        help='первая страница',
        default=1,
        type=int,
    )
    parser.add_argument(
        '--end_page',
        help='последняя страница',
        default=10,
        type=int
    )
    parser.add_argument(
        '--skip_imgs',
        help='не скачивать картинки',
        action='store_const',
        const=True
    )
    parser.add_argument(
        '--json_path',
        help='путь к файлу с описанием книг',
        action='store',
        default=''
    )
    parser.add_argument(
        '--dest_folder',
        help='путь к каталогу с результатами',
        action='store',
        default=''
    )
    parser.add_argument(
        '--skip_txt',
        help='не скачивать книги',
        action='store_const',
        const=True
    )
    args = parser.parse_args()

    books_path = Path(args.dest_folder, 'books')
    images_path = Path(args.dest_folder, 'images')
    descriptions_path = Path(args.dest_folder, args.json_path)

    os.makedirs(books_path, exist_ok=True)
    os.makedirs(images_path, exist_ok=True)
    os.makedirs(descriptions_path, exist_ok=True)

    for page_number in range(args.start_page, args.end_page + 1):
        url = f'https://tululu.org/l55/{page_number}'
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')
        book_cards = soup.select('table.d_book')

        for book_card in book_cards:
            book_id = re.search(r'\d+', book_card.select_one('a')['href'])[0]
            book_url = f'https://tululu.org/b{book_id}'

            response = requests.get(book_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')

            if not args.skip_txt:
                download_txt(soup, book_id, books_path)
            if not args.skip_imgs:
                download_image(soup, images_path)

            book_description = parse_book_description(soup)
            book_descriptions.append(book_description)

    with open(
            f'{descriptions_path}/descriptions.json',
            'w',
            encoding='utf8'
    ) as file:
        json.dump(book_descriptions, file, ensure_ascii=False)


if __name__ == '__main__':
    main()
