# Scrapy-Splash Jobs Web Scraping

This project aims to scrape job listings from various websites using Scrapy-Splash. The target websites for scraping include Bumeran, Indeed, Computrabajo, and LinkedIn.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Spiders](#spiders)
- [Contributing](#contributing)
- [License](#license)

## Installation

To get started with this project, follow these steps:

1. **Clone the repository:**
    ```bash
    git clone https://github.com/Piero7210/jobs_scrapy-splash.git
    cd job-scraper
    ```

2. **Create a virtual environment (optional but recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Install and start Splash:**

    You can run Splash using Docker:
    ```bash
    docker pull scrapinghub/splash
    docker run -p 8050:8050 scrapinghub/splash
    ```

## Usage

To run the web scraping process, execute the following command:

```
scrapy crawl job_spider
```

To run a spider, use the Scrapy command line tool. For example, to run the LinkedIn spider:

```bash
scrapy crawl linkedin_spider
```

Make sure to customize the spider settings and parameters according to your requirements.

## Output

The scraped job listings will be saved in a SQL database.

## Contributing

Contributions are welcome! If you encounter any issues or have suggestions for improvement, please open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
