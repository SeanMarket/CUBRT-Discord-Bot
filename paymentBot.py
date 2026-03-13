import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import gspread
from google.oauth2.service_account import Credentials
from dataclasses import dataclass



#-----------Sheets Init-----------#
scopes = [
    "https://www.googleapis.com/auth/spreadsheets"
]

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
sheetsClient = gspread.authorize(creds)



#-----------Discord Init-----------#
load_dotenv()

token = os.getenv('DISCORD_TOKEN') #discord api bringing bot online

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='$', intents=intents) 





def pullSheet():
    sheet_id = "1P9k89U1hkDVZM9Y-OSiMETQM-WY3La-bae6zBPjC5ho" #Refresh the sheet every time there is a new reaction
    print(sheet_id)
    sheet = sheetsClient.open_by_key(sheet_id)
    print("Successfully opened the sheet")
    values_list = sheet.sheet1.col_values(3)


    lowerList = []
    for person in values_list: #convert to lowercase to avoid capitalization errors
        lowerList.append(person.lower())

    print("Successfully obtained values")
    return lowerList
    


@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}") #write to terminal when bot is ready

#watch for reactions on a message

mechanicRole = "Mechanic"
discordClient = discord.Client(intents=intents)
messageID = "1411892429409226802"


@bot.event
async def on_raw_reaction_add(payload):

    guild = bot.get_guild(payload.guild_id) #Get the ID of the message that was reacted to
    role = discord.utils.get(guild.roles, name=mechanicRole) #find the Mechanic role
    member = guild.get_member(payload.user_id) #get the user who reacted

    # memberName = (member.name).lower convert to lowercase to avoid capitalization errors

    print(member.name + ':')

    

    payloadMID = str(payload.message_id)

    if(payloadMID == messageID):
        memberList = pullSheet()
        

        for person in memberList:
            print(person)
            if person == member.name.lower():
                await member.add_roles(role) #horrible time complexity, but I don't feel like creating a data structure
                counter = counter + 1



    #WIP for just checking sheet and checking server, removing the need to react to the message.
    # for user in guild.members:
    #     for sheetMember in memberList:
    #         if(user == sheetMember):
    #             addRole = guild.


        print("Counter: " + counter)
    else:
        return
    
    




@bot.command()
async def verifyRoles(ctx):
    await ctx.send(f"Verifying roles...")

    messageID = "1411892429409226802"
    channelID = "1026915074377519175"

    channel = ctx.guild.get_channel(int(channelID))

    message =  await channel.fetch_message(int(messageID))

    # await ctx.send(message)

    users = []

    for reaction in message.reactions:
        async for user in reaction.users():
            users.append(user.name)

    #have to convert usernames into member objects. Member objects contain user IDs which are needed to add roles.
    members = []

    for member in ctx.guild.members:
        for user in users:
            if user == member.name.lower():
                members.append(member)




    role = discord.utils.get(ctx.guild.roles, name=mechanicRole)
    memberList = pullSheet()

    counter = 0
  
    for member in memberList: #memberList is a list of lowercase names
        for person in members: #members is a list of member objects
            print(person.name.lower())
            if person.name.lower() == member:
                await person.add_roles(role) #horrible time complexity, but I don't feel like creating a data structure

#-----------Driver Sheet-----------#



@dataclass
class Person:
    name: str
    rowNum: int

drivers = {}
global row #Start at 2 because row 1 is headers
row = int(2)
def pullDriverSheet():
    sheet_id = os.getenv('DRIVER_SHEET')
    print(sheet_id)
    sheet = sheetsClient.open_by_key(sheet_id)
    print("Successfully opened driver sheet")
    driver_list = sheet.sheet1.col_values(1)
    driver_list.remove("Driver") #first element in column A is always driver

    global row
    for person in driver_list: #hash each driver's name and use the hash key as key and driver name as value
        driver = Person(str(person), row)
        drivers.update({hash(person):driver})
        row += 1

    print("Successfully obtained drivers")
    return drivers



@bot.command()
async def displayDrivers(ctx):
    drivers = pullDriverSheet()
    await ctx.send(drivers)


@bot.command()
async def addDriver(ctx, first, last):
    name = str(first) +' ' + str(last)

    if not drivers.get(hash(name)):
        await ctx.send("Adding: " + str(name) + " to the driver list")
        row +=1
        drivers.update({hash(name):Person(name, row)})
        return
    
    await ctx.send("Driver " + str(name) + " already in sheet")
            



#-----------Personal Commands-----------#
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

@bot.command()
async def jake(ctx): 
    await ctx.send(f"Fuck you")

@bot.command()     
async def verifyHoles(ctx):
    await ctx.send(f"Jake verified")

@bot.command()
async def freakybob(ctx):
    await ctx.send(f"Jake is a freakybob")

@bot.command()
async def carson(ctx):
    await ctx.send(f"CARSON???")

@bot.command()
async def sean(ctx):
    await ctx.send(f"Stinky CS major")

@bot.command()
async def tripp(ctx):
    await ctx.send(f"Last seen at shop: 1000000 Days Ago")

@bot.command()
async def retard(ctx):
    await ctx.send(f"Where's Jake at")

@bot.command()
async def mike(ctx):
    await ctx.send(f"Congrats! Back to the dorms")

@bot.command()
async def austin(ctx):
    await ctx.send(f"Austin MacAbsolutelyFilthyBecauseHeWasDiggingAroundATransmissionAndGotCoveredInGreaseAndOil")

@bot.command()
async def dom(ctx):
    await ctx.send(f"That's too much money")

@bot.command()
async def chazbo(ctx):
    await ctx.send(f"📷")


bot.run(token, log_handler=handler, log_level=logging.DEBUG)
