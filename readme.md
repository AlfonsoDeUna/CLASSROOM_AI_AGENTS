# Google Classroom Submission Scraper & Downloader (v3)

A powerful Python automation bot powered by **Playwright** that navigates Google Classroom, extracts student submission data, and automatically downloads attached assignments as PDFs.

## author: Alfonso de Uña

##  Key Features

* **Submission Extraction:** Scrapes student names, IDs, and submission statuses.
* **File Discovery:** Identifies attached Google Docs, Slides, Sheets, and uploaded PDFs.
* **Auto-Conversion:** Automatically converts and downloads Google Docs/Slides/Sheets as **PDFs**.
* **Persistent Login:** Uses a temporary Chrome profile to maintain sessions and reduce login attempts.
* **Data Export:** Generates a structured `.json` file containing all class and submission metadata.
* **Smart Naming:** Renames downloaded files using the format: `StudentName_FileID.pdf` for easy organization.

## Prerequisites

* Python 3.8+
* Google Chrome (or Chromium) installed.

##  Installation

1.  **Clone or download the repository.**
2.  **Install the required Python packages:**

    ```bash
    pip install playwright
    ```

3.  **Install the Playwright browsers:**

    ```bash
    playwright install chromium
    ```

##  Usage

1.  Run the script:

    ```bash
    python bot3_copy.py
    ```

2.  **Authentication:**
    * The bot will prompt for your Google Email and Password.
    * *Note:* You can also set them as environment variables `GOOGLE_EMAIL` and `GOOGLE_PASSWORD` to skip the prompt.

3.  **Navigation:**
    * Follow the numbered on-screen menu to select the **Class** and the **Assignment (Tarea)**.
    * If the bot cannot auto-detect the assignment list, you can manually paste the Assignment ID (found in the URL).

4.  **Extraction & Download:**
    * The bot will scan all students.
    * It will generate a `.json` summary.
    * It will ask if you want to download the files as PDFs. If yes, files are saved in the `descargas_Tarea_manual` folder.

## Important Disclaimer

* **Educational Use Only:** This tool is intended for personal productivity and educational purposes to assist teachers in archiving work.
* **Google Terms of Service:** Automated scraping may violate Google's Terms of Service. Use this tool responsibly, do not spam requests, and avoid running it at high frequency to prevent your account from being flagged or temporarily locked.
* **Privacy:** Handle the downloaded student data in compliance with your institution's privacy policies (e.g., GDPR, FERPA).

---

##  Roadmap & Future Improvements

###  Access Management
* **OAuth 2.0 Integration:** Replace raw password handling with Google OAuth 2.0 flows to improve security and avoid storing sensitive credentials in memory.
* **Cookie/Session Management:** Implement a robust cookie export/import mechanism to survive browser restarts without re-logging in manually.
* **2FA Handling:** Add an interactive wait state or UI prompt to handle Two-Factor Authentication challenges gracefully.

###  Output Improvements
* **Dynamic Folder Structure:** Allow the user to define the output path (e.g., `./Downloads/{ClassName}/{AssignmentName}/`).
* **Format Selection:** Add options to download files in their original format (`.docx`, `.pptx`) instead of forcing PDF.
* **CSV Export:** Generate a `.csv` gradebook-style export alongside the JSON file for easier Excel integration.
* **Log Rotation:** Implement the `logging` module to save execution logs to files for debugging purposes.

###  Menus & CLI Experience
* **Rich UI:** Replace standard `print()` statements with the `Rich` or `InquirerPy` libraries for interactive arrow-key menus, progress bars, and colored terminal output.
* **Headless Switch:** Add a command-line argument (e.g., `--headless`) to run the browser in the background without a visible window.
* **Config File:** Support a `config.yaml` file to save default preferences (download paths, headless mode, timeout settings).

###  Web Interface (GUI)
* **Web Dashboard:** Wrap the bot logic in a **Streamlit** or **Flask** application to provide a user-friendly web interface.
    * *Upload:* Allow users to upload a `credentials.json`.
    * *Visual Select:* Show classes and assignments in dropdowns.
    * *One-Click Download:* Button to trigger the scrape and serve the result as a `.zip` file download.
