# iOS Signal DB Visualizer
The db parser will generate a datamodel compatible with the fronted.  
Inside the chat you can play videos/audios, see images/stickers, open documents ecc.. (**group container is mandatory**)  

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


**The fronted is an edited version of this:** https://github.com/anishghosh103/whatsapp   
<p>&nbsp;</p>  
  
![Screenshot](https://github.com/fr3ns1s/iOS_Signal_Visualizer/blob/main/screenshot.png )
