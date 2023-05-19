from machine import Pin,I2C
import network
import aioespnow
import uasyncio as asio
import ssd1306
from time import sleep_ms,sleep

# A WLAN interface must be active to send()/recv()
network.WLAN(network.STA_IF).active(True)

e = aioespnow.AIOESPNow()  # Returns AIOESPNow enhanced with async support
e.active(True)
peer = b'\xE0\x5A\x1B\x75\x7D\x04' #E05A1B757D04
e.add_peer(peer)

i2c = I2C(0, sda=Pin(21), scl=Pin(22))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)
push_button = Pin(0, Pin.IN)

no_msg=True
col_sel=0
color=['Red','Yellow','White','Green','Black','Cyan','Blue','Magenta']

# Received messages
async def resive(e,int_ms):
    global no_msg
    while 1:
        async for mac, msg in e:
            no_msg=False
            oled.fill(0)
            oled.text('Find: '+color[col_sel], 10, 10)
            oled.text(msg.decode("utf-8").split(' ')[0] , 10, 20)
            oled.text(msg.decode("utf-8").split(' ')[1] , 10, 30)
            oled.text(msg.decode("utf-8").split(' ')[2] , 10, 40)
            oled.show()
            await asio.sleep_ms(int_ms) 

async def no_connect(int_ms):
    global no_msg
    while 1:
        no_msg=True
        await asio.sleep_ms(int_ms) 
        if no_msg:
            oled.fill(0)
            oled.text('No connect', 10, 10)
            oled.show()

async def button_sel(int_ms):
    global col_sel
    while 1:
        if push_button.value()==0:
            if col_sel<7:
                col_sel+=1
            else:
                col_sel=0
            if col_sel==4:
                col_sel=5
            if col_sel==2:
                col_sel=3
        await asio.sleep_ms(int_ms)
        
async def send(e, period):
    while 1:
        await e.asend(str(col_sel)) 
        await asio.sleep_ms(period)

# define loop
loop = asio.get_event_loop()

#create looped tasks
loop.create_task(no_connect(500))
loop.create_task(resive(e,100))
loop.create_task(button_sel(300))
loop.create_task(send(e, 200))

# loop run forever
loop.run_forever()