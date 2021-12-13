import argparse
import json
import re
import os
from urllib.parse import urljoin, urlsplit, unquote
from pathlib import Path

from bs4 import BeautifulSoup
from pathvalidate import sanitize_filename
import requests


def check_for_redirect(response):
    if response.history:
        raise requests.HTTPError


def download_image(image_url, images_path):
    response = requests.get(image_url)
    response.raise_for_status()
    check_for_redirect(response)

    image_path_url = urlsplit(image_url).path
    filename = unquote(os.path.split(image_path_url)[1])
    path = Path(images_path, filename)

    with open(path, 'wb') as file:
        file.write(response.content)


def download_txt(book_title, book_id, books_path):
    book_url = "https://tululu.org/txt.php"
    payload = {'id': book_id}

    filename = '{}. {}'.format(book_id, book_title)
    clean_filename = f"{sanitize_filename(filename)}.txt"
    path = Path(books_path, clean_filename)

    response = requests.get(book_url, params=payload)
    response.raise_for_status()
    check_for_redirect(response)

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

    url_image = urljoin(
        'https://tululu.org',
        soup.select_one('div.bookimage img')['src'],
    )

    book_description = {
        'title': title.strip(),
        'author': author.strip(),
        'genres': genres,
        'comments': comments,
        'cover': url_image
    }
    return book_description


def save_descriptions(descriptions_path, book_descriptions):
    with open(
            f'{descriptions_path}/descriptions.json',
            'w',
            encoding='utf8'
    ) as file:
        json.dump(book_descriptions, file, ensure_ascii=False)


def get_user_arguments():
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
        default=get_last_page_number(),
        type=int,
    )
    parser.add_argument(
        '--skip_imgs',
        help='не скачивать картинки',
        action='store_true',
    )
    parser.add_argument(
        '--json_path',
        help='путь к файлу с описанием книг',
        action='store',
        default='',
    )
    parser.add_argument(
        '--dest_folder',
        help='путь к каталогу с результатами',
        action='store',
        default='',
    )
    parser.add_argument(
        '--skip_txt',
        help='не скачивать книги',
        action='store_true',
    )
    args = parser.parse_args()
    return args


def get_last_page_number():
    url = f'https://tululu.org/l55/'
    response = requests.get(url)
    response.raise_for_status()
    check_for_redirect(response)

    soup = BeautifulSoup(response.text, 'lxml')
    end_page = soup.select_one('table a.npage:last-child').contents[0]
    return int(end_page)


def main():
    books_descriptions = []
    user_args = get_user_arguments()

    books_path = Path(user_args.dest_folder, 'books')
    images_path = Path(user_args.dest_folder, 'images')
    descriptions_path = Path(user_args.dest_folder, user_args.json_path)

    os.makedirs(books_path, exist_ok=True)
    os.makedirs(images_path, exist_ok=True)
    os.makedirs(descriptions_path, exist_ok=True)

    for page_number in range(user_args.start_page, user_args.end_page + 1):
        url = f'https://tululu.org/l55/{page_number}/'
        response = requests.get(url)
        response.raise_for_status()
        try:
            check_for_redirect(response)
        except requests.HTTPError:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        books_cards = soup.select('table.d_book')

        for book_card in books_cards:
            book_id = re.search(r'\d+', book_card.select_one('a')['href'])[0]
            book_url = f'https://tululu.org/b{book_id}/'

            response = requests.get(book_url)
            response.raise_for_status()

            try:
                check_for_redirect(response)
                soup = BeautifulSoup(response.text, 'lxml')

                book_description = parse_book_description(soup)
                books_descriptions.append(book_description)

                if not user_args.skip_txt:
                    download_txt(
                        book_description['title'],
                        book_id,
                        books_path,
                    )
                if not user_args.skip_imgs:
                    image_url = book_description['cover']
                    download_image(image_url, images_path)

            except requests.HTTPError:
                pass

    save_descriptions(descriptions_path, books_descriptions)


if __name__ == '__main__':
    main()
