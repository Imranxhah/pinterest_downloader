# Pinterest Downloader

A GUI and script-based Pinterest image scraper built with Selenium.

## Features
- **GUI Application (`app.py`)**: A modern interface to scrape Pinterest images and save them to CSV.
- **Standalone Script (`scrapper.py`)**: A simple script version for quick scraping.
- **Auto-Login**: Handles Pinterest authentication.
- **Incremental Scraping**: Appends new links to existing CSVs without duplicates.

## Installation
1. Clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
### GUI App
Run `python app.py` to launch the graphical interface.

### Script
1. Update your credentials in `scrapper.py`.
2. Run `python scrapper.py`.

## License
MIT
