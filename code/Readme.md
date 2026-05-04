In this folder (`code`) you will find the actual functions that make the app run. 

## Before you start
First make sure that you have all modules installed that are defined in the `requirements.txt`. You may also use the conda environment indicated in `environment.yml`. 

For using a conda environment use the following command in the terminal. Make sure that the path/folder is set correctly in the main directory of this project. 

    conda env create --name software_dev_powergen --file=code/environments.yml 

If you prefer to use only pip you may install the packages using the `requirements.txt` file by typing into the terminal: 

    pip install -r code/requirements.txt

For running the streamlit app, open a terminal and make sure that the working directory is set at this repo.
Then put in the terminal:  

    streamlit run .\code\main.py
A new browser tab should open in your browser with localhost as URL and our app as content. 
   
## Notes
Note that `main.py` only includes the function calls to make it short and sweet. Most of the actual text and functions are in the files `dashboard.py` and `preprocess.py`. All functions are fully documented with docstrings. 