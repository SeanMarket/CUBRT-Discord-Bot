import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import gspread
from google.oauth2.service_account import Credentials
from dataclasses import dataclass
import time
from commands import *
import timeit




#-----------Sheets Init-----------#
scopes = [
    "https://www.googleapis.com/auth/spreadsheets"
]

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
sheetsClient = gspread.authorize(creds)

SHEET_ID = os.getenv('PAYMENT_SHEET')



#-----------Discord Init-----------#
load_dotenv()

token = os.getenv('DISCORD_TOKEN') #discord api bringing bot online

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='$', intents=intents)

#-----------Payment-----------#
MEMBERCOL = 5

def pullSheet() -> dict:#returns list of members who have filled out the Google Form
    print("Sheet id: " + SHEET_ID)
    sheet = sheetsClient.open_by_key(SHEET_ID)
    print("Successfully opened the sheet")
    valuesList = sheet.sheet1.col_values(MEMBERCOL)

    #TODO Find capitalization bug and fix it
    lowerList = {}
    print("Creating lowerList")
    for person in valuesList:
        lowerList.update({hash(person.lower()):person.lower()})

    #TODO look at difference in number of entries in the sheet and compare to entries in lowerList. If different, add the difference. Much more efficient than pulling the entire sheet every refresh.

    print("Successfully obtained lowerlist")
    return lowerList 
    


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    print(f"Creating dictionary")

    guild = bot.get_guild(int(os.getenv('GUILD')))
    global members
    members = {}

    for member in guild.members:
        members.update({hash(member.name.lower()):member})

    print(f"Dictionary created")
    print(f"Bot awaiting commands")
        

    #TODO add driver sheet init



MECHANIC_ROLE = "Mechanic"
DISCORD_CLIENT = discord.Client(intents=intents)
MESSAGE_ID = int(os.getenv('MESSAGE_ID')) #TODO update every year

@bot.command()
async def verifyRoles(ctx):
    global members
    

    await ctx.send("Verifying roles...")
    print("Verifying roles...")

    role = discord.utils.get(ctx.guild.roles, name=MECHANIC_ROLE)
    sheetEntries = pullSheet()

    print("Checking sheet against members")

    # startVerification = time.perf_counter()
    for key in sheetEntries: #Compares the names on the sheet to the names of people in the server, rather than comparing users who reacted to the message to users in the server.
        # print(f"Verifying roles for {current - start:0.4f} seconds")
        print(members.get(key))
        if members.get(key):
            # startAssign = time.perf_counter()
            await members.get(key).add_roles(role)
            # endAssign = time.perf_counter() 
            # print("Time for assignment: " + str(endAssign-startAssign))
            #Not too sure about how much more efficient this can be made. Discord rate limiting greatly impacts performance
        
    # endVerification = time.perf_counter()
    # print("Total verification time: " + str(endVerification - startVerification))
    print("All roles verified")


@bot.command() #This loop removes the need to watch for reactions to the member dues message. Instead, the bot will execute verifyRoles once an hour. This is useful for initial member dues collection, when there are many form submissions in a short period of time.
async def idleAssign(ctx):
    while True:
        time.sleep(3600)
        await verifyRoles(ctx)

#-----------Driver Sheet-----------#

@dataclass(frozen=True)
class Person:
    name: str
    rowNum: int


FIRST_ROW = 2
DRIVER_WORKSHEET = 0

drivers = {}
row = int(FIRST_ROW) #init to 2 because first row is headers. Is equal to next free row
worksheet = None


def pullDriverSheet() -> None:#Call this with every sheet update so the bot can see changes while running
    global worksheet
    global row

    sheetId = os.getenv('DRIVER_SHEET') 
    print(sheetId)
    driverSheet = sheetsClient.open_by_key(sheetId)
    worksheet = driverSheet.get_worksheet(DRIVER_WORKSHEET)
    print("Successfully opened driver sheet")

    driver_list = driverSheet.sheet1.col_values(1)
    driver_list.remove("Driver") #first element in column A is always driver

    for person in driver_list: #hash each driver's name and use the hash key as key and driver name as value
        #TODO make this not run every time pullDriverSheet is called
        driver = Person(str(person), row)

        if drivers.get(hash(person)): #check to see if driver is already in dictionary
            continue
        
        drivers.update({hash(person):driver})
        row += 1 #sets row to next free row

    print("Successfully obtained drivers")



# @bot.command() #Debugging function
# async def displayDrivers(ctx):
#     await ctx.send(drivers)


@bot.command()
async def addDriver(ctx, first:str, last:str) -> None:
    global row

    name = str(first) +' ' + str(last)

    if not drivers.get(hash(name)):
        print("Adding: " + name + " to the driver list")
        drivers.update({hash(name):Person(name, row)})
        worksheet.update_cell(row, NAMECOL, first + ' ' + last)
        row += 1
        return
    
    print("Driver " + name + " already in sheet")


def findDriverRow(first:str, last:str) -> int:
    name = str(first) +' ' + str(last)
    driver = drivers.get(hash(name))
    driverRow = driver.rowNum
    return driverRow
    

async def getMessage(ctx) -> str:

    def check(message):
        return message.author == ctx.author and message.channel == ctx.channel
    
    user_reply = await bot.wait_for("message", check=check)

    value = user_reply.content.strip() #strip method removes leading and trailing whitespace

    return value

def isEmpty(row:int, col:int) -> bool:
    val = worksheet.cell(row,col).value

    if val == None:
        return True
    else:
        return False
    
def getEmptyCell(row:int) -> int: #finds next empty row
    i = 1
    while worksheet.cell(row, i).value != None:
        i += 1
    return i
    

def parseLapTime(lapTime: str) -> float:
    minutesPart, secondsPart = lapTime.split(":") #split laptimes to allow for easier calculation. 01:23.42 -> minutesPart = 1, secondsPart = 23.42
    minutes = int(minutesPart)
    seconds = float(secondsPart)
    return minutes * 60 + seconds

def formatLapTime(totalSeconds: float) -> str: #takes the total seconds from parseLapTime and formats it back into mm:ss.xx
    minutes = int(totalSeconds // 60)
    seconds = totalSeconds % 60
    return f"{minutes:02}:{seconds:05.2f}"

def averageLapTimes(lapTimes: list[str]) -> str:
    total = sum(parseLapTime(time) for time in lapTimes)
    average = total / len(lapTimes)
    return formatLapTime(average)


eventName = None

@bot.command()
async def createEvent(ctx):
    global eventName
    await ctx.send(f"Enter event name: ")
    eventName = await getMessage(ctx)
    await ctx.send(f"Setting event to " + eventName)

skipTime = False
@bot.command() #this function is useful when entering bulk driver data without knowing the number of timed laps and/or times. Otherwise just put N/A when prompted
async def skipTimed(ctx):
    global skipTime
    skipTime = True
    await ctx.send(f"Skipping timed laps")

NAMECOL  = int(1)
MANUALCOL = int(2)
EXPERIENCECOL = int(3)
HEADERROW = int(1)

@bot.command()
async def addData(ctx, first:str, last:str)->None:
    global eventName
    global skipTime

    pullDriverSheet()
    await addDriver(ctx, first, last) #Check if driver is already in sheet or not, and find the driver
    driverRow = findDriverRow(first, last)

    if worksheet.cell(driverRow, NAMECOL) == None:
        worksheet.update_cell(driverRow, NAMECOL, first + ' ' + last)
    

    if isEmpty(driverRow, MANUALCOL): #add manual driving experience if not already in sheet
        await ctx.send(f"Can they heel-toe?")
        value = await getMessage(ctx)
        worksheet.update_cell(driverRow, MANUALCOL, value)
        print(first +' '+ last + " manual set to: " + str(value))
    
    if isEmpty(driverRow, EXPERIENCECOL): #add prior racing experience if not already in sheet
        await ctx.send(f"List any prior driving experience (not CUBRT-related)")
        value = await getMessage(ctx)
        worksheet.update_cell(driverRow, EXPERIENCECOL, value)
        print(first +' '+ last + " Experience: " + str(value))

    emptyCol = getEmptyCell(driverRow) #Empty cell is the next empty cell in the driver row. Populating sheet from left to right

    if eventName == None:
        await ctx.send("Enter event name")
        eventName = await getMessage(ctx)
    
    if(worksheet.cell(row,emptyCol).value == None): #add event column header if needed
        worksheet.update_cell(HEADERROW, emptyCol, "Event")

    worksheet.update_cell(driverRow, emptyCol, eventName)

    await ctx.send("Enter fastest lap (MM:SS.XX). If not applicable, type N/A")
    fastLap = await getMessage(ctx)

    if(worksheet.cell(row,emptyCol+1).value == None): #add fast lap column header if needed
        worksheet.update_cell(HEADERROW, emptyCol+1, "Fast lap")

    worksheet.update_cell(driverRow, emptyCol + 1, fastLap)

    if(worksheet.cell(row,emptyCol+2).value == None): #add average lap column header if needed
            worksheet.update_cell(HEADERROW, emptyCol+2, "Avg Lap")

    if skipTime:
        worksheet.update_cell(driverRow, emptyCol + 2, "N/A")
    else: 
        await ctx.send("Enter number of timed laps. If not applicable, type N/A")
        numLaps = await getMessage(ctx)

        if numLaps == "N/A":
            worksheet.update_cell(driverRow, emptyCol + 2, "N/A")
        else: #Input the number of timed laps and calculate the average
            #TODO Add this logic to averageLapTimes function
            i = 1
            times = []
            temp = []
            while(i <= int(numLaps)):
                await ctx.send("Enter time for lap " + str(i) + " (MM:SS.XX)")
                lapTime = await getMessage(ctx)

                temp = lapTime.split(":") #split returns list of separated pieces
                while(len(temp) != 2):
                    await ctx.send("Make sure format is in MM:SS.XX")
                    lapTime = await getMessage(ctx)
                    temp = lapTime.split(":")

                times.append(lapTime)
                i +=1

            average = averageLapTimes(times)

            worksheet.update_cell(driverRow, emptyCol + 2, average)

    await ctx.send("Enter notes")


    notes = await getMessage(ctx)

    if(worksheet.cell(row,emptyCol+3).value == None):
        worksheet.update_cell(HEADERROW, emptyCol + 3, "Notes")
    
    worksheet.update_cell(driverRow, emptyCol + 3, notes)



@bot.command()
async def addNotes(ctx, first:str, last:str)->None: #bypass all timing information (both fast lap and avg lap). Useful when we are not timing laps but are still taking notes
    global eventName


    pullDriverSheet()
    await addDriver(ctx, first, last)

    driverRow = findDriverRow(first, last)

    if worksheet.cell(driverRow, NAMECOL) == None:
        worksheet.update_cell(driverRow, NAMECOL, first + ' ' + last)

    emptyCol = getEmptyCell(driverRow)

    if eventName == None:
        await ctx.send("Enter event name")
        eventName = await getMessage(ctx)
    

    #TODO Add these next couple of checks to a stand-alone function
    if(worksheet.cell(row,emptyCol).value == None):
        worksheet.update_cell(HEADERROW, emptyCol, "Event")

    worksheet.update_cell(driverRow, emptyCol, eventName)


    if(worksheet.cell(row,emptyCol+1).value == None): #fill in fast lap and avg lap columns to maintain formatting. When using this function, only event name and notes are requested.
        worksheet.update_cell(HEADERROW, emptyCol+1, "Fast lap")

    worksheet.update_cell(driverRow, emptyCol + 1, "N/A")

    if(worksheet.cell(row,emptyCol+2).value == None):
            worksheet.update_cell(HEADERROW, emptyCol+2, "Avg Lap")

    worksheet.update_cell(driverRow, emptyCol + 2, "N/A")


    await ctx.send("Enter notes")


    notes = await getMessage(ctx)

    if(worksheet.cell(row,emptyCol+1).value == None):
        worksheet.update_cell(HEADERROW, emptyCol + 1, "Notes")
    
    worksheet.update_cell(driverRow, emptyCol + 1, notes)

    
   
#-----------Personal Commands-----------#
@bot.command()
async def hello(ctx):
    await helloFunc(ctx)

@bot.command()
async def jake(ctx): 
    await jakeFunc(ctx)

@bot.command()     
async def verifyHoles(ctx):
    await verifyHolesFunc(ctx)

@bot.command()
async def freakybob(ctx):
    await freakyBobFunc(ctx)

@bot.command()
async def carson(ctx):
    await carsonFunc(ctx)

@bot.command()
async def sean(ctx):
    await seanFunc(ctx)

@bot.command()
async def tripp(ctx):
    await trippFunc(ctx)

@bot.command()
async def mike(ctx):
    await mikeFunc(ctx)

@bot.command()
async def austin(ctx):
    await austinFunc(ctx)    

@bot.command()
async def dom(ctx):
    await domFunc(ctx)

@bot.command()
async def chazbo(ctx):
    await chazboFunc(ctx)

@bot.command()
async def tobias(ctx):
    await tobiasFunc(ctx)

@bot.command()
async def kai(ctx):
    await kaiFunc(ctx)

@bot.command()
async def liam(ctx):
    await liamFunc(ctx)

@bot.command()
async def tanner(ctx):
    await tannerFunc(ctx)


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
