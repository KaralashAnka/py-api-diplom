
import json
import logging
import os
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse
from tqdm import tqdm


class YandexDiskAPI:


    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://cloud-api.yandex.net/v1/disk"
        self.headers = {
            'Authorization': f'OAuth {token}',
            'Content-Type': 'application/json'
        }

    def create_folder(self, folder_path: str) -> bool:

        url = f"{self.base_url}/resources"
        params = {'path': folder_path}

        response = requests.put(url, headers=self.headers, params=params)

        if response.status_code == 201:
            logging.info(f"Папка '{folder_path}' успешно создана")
            return True
        elif response.status_code == 409:
            logging.info(f"Папка '{folder_path}' уже существует")
            return True
        else:
            logging.error(f"Ошибка создания папки: {response.status_code}")
            return False

    def upload_file_from_url(self, file_url: str, disk_path: str) -> bool:

        url = f"{self.base_url}/resources/upload"
        params = {
            'path': disk_path,
            'url': file_url
        }

        response = requests.post(url, headers=self.headers, params=params)

        if response.status_code == 202:
            logging.info(f"Файл '{disk_path}' успешно загружен")
            return True
        else:
            logging.error(f"Ошибка загрузки файла: {response.status_code}")
            return False


class DogCeoAPI:


    def __init__(self):
        self.base_url = "https://dog.ceo/api"

    def get_all_breeds(self) -> Dict:

        url = f"{self.base_url}/breeds/list/all"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Ошибка получения пород: {response.status_code}")
            return {}

    def get_breed_image(self, breed: str, sub_breed: Optional[str] = None) -> Optional[str]:

        if sub_breed:
            url = f"{self.base_url}/breed/{breed}/{sub_breed}/images/random"
        else:
            url = f"{self.base_url}/breed/{breed}/images/random"

        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return data['message']

        logging.error(f"Ошибка получения изображения для {breed}")
        return None


class DogImageDownloader:


    def __init__(self, token: str):
        self.yandex_api = YandexDiskAPI(token)
        self.dog_api = DogCeoAPI()
        self.results = []

        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('dog_downloader.log'),
                logging.StreamHandler()
            ]
        )

    def extract_filename_from_url(self, url: str) -> str:

        parsed_url = urlparse(url)
        return os.path.basename(parsed_url.path)

    def download_breed_images(self, breed: str, sub_breeds: List[str] = None) -> None:

        folder_path = f"/PY-130(API)/dog_images/{breed}"

        # Создать папку для породы
        if not self.yandex_api.create_folder(folder_path):
            logging.error(f"Не удалось создать папку для породы {breed}")
            return

        images_to_download = []

        # Если есть подпороды, загружаем по одному изображению каждой подпороды
        if sub_breeds:
            for sub_breed in sub_breeds:
                image_url = self.dog_api.get_breed_image(breed, sub_breed)
                if image_url:
                    images_to_download.append({
                        'url': image_url,
                        'breed': breed,
                        'sub_breed': sub_breed
                    })
        else:
            # Если подпород нет, загружаем одно изображение основной породы
            image_url = self.dog_api.get_breed_image(breed)
            if image_url:
                images_to_download.append({
                    'url': image_url,
                    'breed': breed,
                    'sub_breed': None
                })

        # Загружаем изображения с прогресс-баром
        for img_data in tqdm(images_to_download, desc=f"Загрузка {breed}"):
            self.download_single_image(img_data, folder_path)

    def download_single_image(self, img_data: Dict, folder_path: str) -> None:

        url = img_data['url']
        breed = img_data['breed']
        sub_breed = img_data['sub_breed']

        # Создать имя файла
        original_filename = self.extract_filename_from_url(url)
        if sub_breed:
            filename = f"{breed}_{sub_breed}_{original_filename}"
        else:
            filename = f"{breed}_{original_filename}"

        disk_path = f"{folder_path}/{filename}"

        # Загрузить файл
        if self.yandex_api.upload_file_from_url(url, disk_path):
            result = {
                'breed': breed,
                'sub_breed': sub_breed,
                'filename': filename,
                'original_url': url,
                'disk_path': disk_path,
                'status': 'success'
            }
        else:
            result = {
                'breed': breed,
                'sub_breed': sub_breed,
                'filename': filename,
                'original_url': url,
                'disk_path': disk_path,
                'status': 'error'
            }

        self.results.append(result)

    def save_results_to_json(self, filename: str = 'download_results.json') -> None:

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logging.info(f"Результаты сохранены в файл {filename}")

    def run(self, target_breed: str = None) -> None:

        logging.info("Запуск программы загрузки изображений собак")

        # Создать основную папку PY-130(API) если ее нет
        if not self.yandex_api.create_folder("/PY-130(API)"):
            logging.error("Не удалось создать папку PY-130(API)")
            return

        # Создать папку dog_images внутри PY-130(API)
        if not self.yandex_api.create_folder("/PY-130(API)/dog_images"):
            logging.error("Не удалось создать папку dog_images в PY-130(API)")
            return

        # Получить все породы
        breeds_data = self.dog_api.get_all_breeds()
        if not breeds_data or 'message' not in breeds_data:
            logging.error("Не удалось получить список пород")
            return

        breeds = breeds_data['message']

        # Если указана конкретная порода, загружаем только её
        if target_breed:
            if target_breed in breeds:
                sub_breeds = breeds[target_breed] if breeds[target_breed] else []
                self.download_breed_images(target_breed, sub_breeds)
            else:
                logging.error(f"Порода {target_breed} не найдена")
                return
        else:
            # Загружаем все породы
            for breed, sub_breeds in tqdm(breeds.items(), desc="Обработка пород"):
                self.download_breed_images(breed, sub_breeds)

        # Сохранить результаты
        self.save_results_to_json()

        logging.info("Программа завершена")


def main():

    print("=" * 50)
    print("Программа резервного копирования изображений собак")
    print("=" * 50)

    # Ввод породы собаки
    breed = input("Введите породу собаки: ").strip().lower()
    if not breed:
        print("Ошибка: Порода не может быть пустой!")
        return

    # Ввод токена Яндекс.Диска
    token = input("Введите токен Яндекс.Диска: ").strip()
    if not token:
        print("Ошибка: Токен не может быть пустым!")
        return

    print(f"\nЗапуск программы для породы: {breed}")
    print("Начинаем загрузку изображений...\n")

    try:
        # Создание экземпляра загрузчика с введенным токеном
        downloader = DogImageDownloader(token)

        # Запуск загрузки для указанной породы
        downloader.run(target_breed=breed)

        print(f"\n✅ Программа успешно завершена!")
        print(f"Изображения породы '{breed}' сохранены в папке: /PY-130(API)/dog_images/{breed}/")
        print("Результаты сохранены в файле: download_results.json")
        print("Логи сохранены в файле: dog_downloader.log")

    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        print("Проверьте корректность токена и подключение к интернету.")


if __name__ == "__main__":
    main()