from machine import Pin,I2C #работа с выходами GPIO и протоколом связи I2C
from neopixel import NeoPixel #работа с адресными светодиодами (встроена)
from MX1508 import *
from VL53L0X import * #лазерный дальномер
from tcs34725 import * #датчик цвета
from time import sleep_ms,sleep 
import uasyncio as asio
import aioespnow #реализация в асинхронном режиме протокола espNow
import network
import ubinascii

i2c_bus = I2C(0, sda=Pin(16), scl=Pin(17)) #датчик цвета (1-я шина) (программная реализация)
tcs = TCS34725(i2c_bus)
tcs.gain(4)#gain must be 1, 4, 16 or 60 #значение усиления (чем выше, тем больше шума, но можно использовать при низком освещении)
tcs.integration_time(80) #время интегрирования для датчика цвета
i2c_bus1 = I2C(1, sda=Pin(21), scl=Pin(22)) #вторая шина I2C для работы с лазерным дальномером (аппаратная реализация)
tof = VL53L0X(i2c_bus1)
NUM_OF_LED = 1
np = NeoPixel(Pin(33), NUM_OF_LED)
color=['Red','Yellow','White','Green','Black','Cyan','Blue','Magenta']
col_list = set([-1,0,-3,-5])
dir_move=['Stop','Forward','Left','Right','Reverse']
motor_R = MX1508(2, 4)
motor_L = MX1508(27, 14)
Sp=640 #скорость максимальная
Sp1=int(Sp*0.5) #скорость для корректировки
#Sp1=0
Lt=60 
alfa=0.8
debug=1

R_W_count,W_count,col_id,col_id_l,direct,di,dist,busy,busy_col,col_sel=0,0,0,0,-1,0,500,0,0,5 #инициализация глобальных переменных
stop_ms = 500
R_m_pin = Pin(32, Pin.IN) #подключение энкодеров
L_m_pin = Pin(25, Pin.IN)

# A WLAN interface must be active to send()/recv()
network.WLAN(network.STA_IF).active(True) #инициализация wifi-модуля (в виде клиента)
e = aioespnow.AIOESPNow()  # Returns AIOESPNow enhanced with async support (создаем объект, реализующий этот протокол)
e.active(True)
#peer = b'\xC8\xF0\x9E\x52\x66\x0C' #C8F09E52660C (адрес карты, на которую передаем)
###'\\x'+mac[0:2]+'\\x'+mac[2:4]+'\\x'+mac[4:6]+'\\x'+mac[6:8]+'\\x'+mac[8:10]+'\\x'+mac[10:12]
#e.add_peer(peer)
peer = b'\xC8\xF0\x9E\x4E\x9C\xA8' #C8F09E4E9CA8
e.add_peer(peer) #добавление в пакет



def R_W_int(pin): #подсчет количества срабатываний энкодера
    global W_count,R_W_count
    W_count+=1
    R_W_count+=1
    
def L_W_int(pin):
    global W_count
    W_count-=1
    
R_m_pin.irq(trigger=Pin.IRQ_FALLING |Pin.IRQ_RISING , handler=R_W_int) #trigger=Pin.IRQ_FALLING | 
L_m_pin.irq(trigger=Pin.IRQ_FALLING |Pin.IRQ_RISING , handler=L_W_int)

async def synch(int_ms): #корректировка колес для всех направлений движения
    while 1:
        await asio.sleep_ms(int_ms)
        if direct==0: #forward
            if W_count>0:
                motor_R.forward(Sp1)
                motor_L.forward(Sp)
            elif W_count<0:
                motor_R.forward(Sp)
                motor_L.forward(Sp1)
            else:
                motor_R.forward(Sp)
                motor_L.forward(Sp)
        elif direct==1: #left
            if W_count>0:
                motor_R.forward(Sp1)
                motor_L.reverse(Sp)
            elif W_count<0:
                motor_R.forward(Sp)
                motor_L.reverse(Sp1)
            else:
                motor_R.forward(Sp)
                motor_L.reverse(Sp)
        elif direct==2: #right
            if W_count>0:
                motor_R.reverse(Sp1)
                motor_L.forward(Sp)
            elif W_count<0:
                motor_R.reverse(Sp)
                motor_L.forward(Sp1)
            else:
                motor_R.reverse(Sp)
                motor_L.forward(Sp)        
        elif direct==3: #reverse
            if W_count>0:
                motor_R.reverse(Sp1)
                motor_L.reverse(Sp)
            elif W_count<0:
                motor_R.reverse(Sp)
                motor_L.reverse(Sp1)
            else:
                motor_R.reverse(Sp)
                motor_L.reverse(Sp)
        elif direct==-1: #stop
            motor_R.reverse(0)
            motor_L.reverse(0)
            
async def LED_cont(int_ms):
    while 1:
        await asio.sleep_ms(int_ms)
        if col_id==0:
            np[0]=(Lt,0,0)
        elif col_id==1:
            np[0]=(Lt,Lt,0)
        elif col_id==2:
            np[0]=(Lt,Lt,Lt)
        elif col_id==3:
            np[0]=(0,Lt,0)
        elif col_id==4:
            np[0]=(0,0,0)
            np.write()
            await asio.sleep_ms(300)
            np[0]=(Lt,0,0)
            np.write()
            await asio.sleep_ms(300)
        elif col_id==5:
            np[0]=(0,Lt,Lt)
        elif col_id==6:
            np[0]=(0,0,Lt) 
        elif col_id==7:
            np[0]=(Lt,0,Lt)
        np.write()
        '''
        if di==0:
            np[1]=(0,Lt,0)
        elif di==1:
            np[1]=(Lt,Lt,0)
        elif di==2:
            np[1]=(Lt,0,0)
        print(col_id)
        '''
    
async def led_check(int_ms):
    global di,direct,busy_col
    direct = -1
    #motor_R.forward(Sp)
    #motor_L.forward(Sp)
    #mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode().upper()
    #print("MAC: " + mac)
    while 1:
        await asio.sleep_ms(int_ms)
        await color_det()
        await dist_det()
        await asio.sleep_ms(500)
        '''
        np[0]=(Lt,0,0)
        np.write()
        await asio.sleep_ms(500)
        np[0]=(0,Lt,0)
        np.write()
        await asio.sleep_ms(500)
        np[0]=(0,0,Lt)
        np.write()
        await asio.sleep_ms(500)
        '''
        
        
async def Mot_check(int_ms):
    while 1:
        direct = 0
        await asio.sleep_ms(int_ms)
        await color_det()
        await dist_det()
        motor_R.reverse(Sp)
        motor_L.reverse(Sp)
        await asio.sleep_ms(int_ms)
        motor_R.forward(Sp)
        motor_L.forward(Sp)
        
async def move(turn): #движение
    global R_W_count,busy,direct
    busy=1
    R_W_count=0
    while R_W_count<turn:   
        await asio.sleep_ms(0)
    direct = -1
    asio.sleep_ms(70)
    busy=0

        
async def color_det():
    while 1:
        await asio.sleep_ms(100)
        global col_id,col_id_l
        rgb=tcs.read(1)
        r,g,b=rgb[0],rgb[1],rgb[2]
        h,s,v=rgb_to_hsv(r,g,b)
        if 0<h<60:#red
            col_id_l=col_id
            col_id=0
        elif 61<h<120:#yellow
            col_id_l=col_id
            col_id=1
        elif 121<h<180: 
            if v>250:#white
                col_id_l=col_id
                col_id=2
            elif v<55:#black
                col_id_l=col_id
                col_id=4
            #elif 62<v<290:#green
            elif s>52:
                col_id_l=col_id
                col_id=3
        elif 181<h<240:
            if v>100:#cyan
                col_id_l=col_id
                col_id=5
            else:#blue
                col_id_l=col_id
                col_id=6
        elif 241<h<360:#magenta
            col_id_l=col_id
            col_id=7 
        if debug:
            print('Color is {}. R:{} G:{} B:{} H:{:.0f} S:{:.0f} V:{:.0f}'.format(color[col_id],r,g,b,h,s,v))
            
async def dist_det():
    global dist
    tof.start()
    dist_l=dist
    dist=tof.read()-50
    tof.stop()
    dist=int(alfa*dist+(1-alfa)*dist_l)
    if debug:
        print('Distance is {}. W_count {}. R_W_count {}.'.format(dist,W_count,R_W_count))
        

async def W_sp(int_ms):
    global di,direct,busy_col
    last_turn = 0
    while 1:
        await asio.sleep_ms(int_ms)
        await dist_det()
        if 100<dist<180:di=1
        elif dist<100:di=2
        else:di=0
        if (not busy) & (not busy_col): #меняем направление движения при наличии препятствия (если не запрещено)
            if di==1:
                if last_turn == 1 or (last_turn == 0 and dist%2):
                    direct=1
                    last_turn = 1
                elif last_turn == 2 or (last_turn == 0 and not dist%2):
                    direct=2
                    last_turn = 2
                await stop(stop_ms)
                await move(5)
            elif di==2:
                last_turn = 0
                direct=3
                await stop(stop_ms)
                await move(10)
            else:
                last_turn = 0
                direct=0
        #await color_det()
        if  col_id==4: #col_id_l==col_id & (если черная линия)
            direct=3
            await stop(stop_ms)
            await move(20)
            direct=2
            await stop(500)
            await move(10)
        #if  col_id==col_sel:#col_id_l==col_id & (если есть совпадение с выбранным цветом)
        if col_id in col_list:
            direct=-1
            busy_col=1
        else: #если меняем цвет на управляющей плате, робот должен развернуться и сойти с гекса
            motor_R.reverse(Sp)
            motor_L.forward(Sp)
            busy_col=0
            
async def stop(ms):
    global direct
    last_dir = direct
    direct = -1
    await asio.sleep_ms(ms)
    direct = last_dir
    
async def send(e, period):
    if busy_col:
        while 1:
            await e.asend(color[col_id]+' '+dir_move[1+direct]+' '+str(dist)) #
            await asio.sleep_ms(period)
        
async def resive(e,int_ms):
    global col_sel
    while 1:
        async for mac, msg in e:
            col_sel=int.from_bytes(msg,'big')-48
            if col_sel in col_list:
                col_list.discard(col_sel)
            #print(color[col_sel])
            await asio.sleep_ms(int_ms)

loop = asio.get_event_loop() #инициализируем цикл из сопрограмм

loop.create_task(synch(1))
#loop.create_task(led_check(100))
#loop.create_task(move(300))
loop.create_task(W_sp(100))
loop.create_task(color_det())
#loop.create_task(Mot_check(100))

loop.create_task(LED_cont(100))
#loop.create_task(send(e,100))
#loop.create_task(resive(e,100))

loop.run_forever() #запускаем