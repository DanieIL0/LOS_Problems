
# Installation Guide

Guide to set up the environment necessary to run the script


## Setup Instructions

1. **Create a Virtual Environment** (optional):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

2. **Install Python Dependencies**:

    You can install the required Python packages using `pip` and the provided `requirements.txt` file:

    ```bash
    pip install -r requirements.txt
    ```

3. **Install FFmpeg**:

    - **Windows**:
        ```bash
        winget install ffmpeg
        ```
        If it doesn't work:
        Download FFmpeg from (https://ffmpeg.org/download.html) and follow the instructions.

    - **Linux**:
        via sudo package-manager:
        ```bash
        sudo apt-get install ffmpeg
        ```

4. **Run the Script**:

    After, you can run the script using Python in the directory of main.py:

    ```bash
    python main.py
    ```