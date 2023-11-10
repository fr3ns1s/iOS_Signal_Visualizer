# iOS Signal DB Visualizer


## How to install

The `requirements.txt` file should list all Python libraries that your notebooks depend on, and they will be installed using:

```
pip3 install -r requirements.txt
```

## How to use
1. Extract Signal app container from your iPhone/backup 
	```
	/var/mobile/Containers/Shared/AppGroup/UUID
	```
	*the right UUID folder contains "grdb" folder*
2. Extract Signal db key from keychain
3. [Decrypt db](https://github.com/Magpol/HowTo-decrypt-Signal.sqlite-for-IOS)
4. Start the script:
	```
	python3 main.py path_decypted_db path_container
	```
5. Enjoy!


**The fronted is an edited version of this:**
https://github.com/anishghosh103/whatsapp

```
![Alt text](file://screenshot.png "a title")
```


