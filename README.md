This application is an example of usage of the Yoctopuce Python library  you can read the original post here  http://www.yoctopuce.com/EN/article/yoctopuce-libraries-github-pypi-and-raspberry-pi


Before starting to use the PiCooker you need to install Yoctopuce PyPI library and configure your Raspbery PI. You will also need a Yocto-Thermocouple connected to your Raspberry PI

Make sure your Raspberry Pi is up-to-date by running "sudo raspi-config" and by selecting "update". Unfortunately, the Raspberry Pi USB bug is still not completely fixed. You must therefore make sure that your /boot/cmdline.txt file contains the dwc_otg.speed=1 option. When these two operations are performed, you are ready to install the Python library. 

If you have never installed a library from PyPI, you must install the pip tool enabling you to download and install a PyPI package. If you have used pip previously on your Raspberry Pi, you can skip this step which is described in the following paragraph. 

To install pip , you need the setuptools package. Install it with the sudo apt-get install python-setuptools command. Then, to install pip itself, there are several methods which are described on this page. On the Raspberry, the simplest is to install the package python-pip. 

  	sudo apt-get install python-pip

When pip is installed, simply run the pip install command to install a PyPI package. To install the Yoctopuce library, you must therefore run: 

	pip install yoctopuce

Easy, right? pip automatically downloads and installs the most recent library on your machine in the correct directory. To check that the installation went well, you can launch a Python interpreter and run the following lines: 

	pi@raspberrypi ~ $ python
	Python 2.7.3 (default, Jan 13 2013, 11:20:46)
	[GCC 4.6.3] on linux2
	Type "help", "copyright", "credits" or "license" for more information.
	>>> from yoctopuce.yocto_api import *
	>>> print(YAPI.GetAPIVersion())
	1.01.11026 (1.01.11026)
	>>>


We took this opportunity to improve the PiCooker, our small example which monitors cooking with a Raspberry Pi. You can download the new version on GitHub. We added the possibility to use several temperature sensors, connected to the same Raspberry Pi. As a reminder, the command line to run the PiCooker looks like this: 

	./picooker.py --smtp_host=smtp.gmail.com --smtp_port=465 --smtp_user=myemail@gmail.com --smtp_pass=mypassword

Naturally, your must adapt these parameters depending on your email and internet providers. The correct SMTP port can be 25, 465, or 587. In case of doubt, try them one after the other until you find the one that works. To make your life easier, this new version of the software sends a test email at start-up to check that the SMTP parameters are correct.
