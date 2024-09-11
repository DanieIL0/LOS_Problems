
# Installation Guide

Guide to set up the environment necessary to run the script.

## Requirements

- **Python 3.x**

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

    - **macOS**:
        via Homebrew:
        ```bash
        brew install ffmpeg
        ```

    - **Linux**:
        via sudo package-manager:
        ```bash
        sudo apt-get install ffmpeg
        ```

4. **Adjust Config**:
    adjust the config.py file if necessary in implementation/shared/config.py

5. **Place Files in correct directory**:
    put all the files into a python directory \ATLASLineOfSight\Pig04\Python


6. **Run the Script**:

    Once all dependencies are installed, you can run the scripts using Python:

    ```bash
    python plot.py
    ```
    to get the plots in the plot directory
    
     ```bash
    python cutvideos.py
    ```
    to get the parts where there are a lot of line of sight issues
