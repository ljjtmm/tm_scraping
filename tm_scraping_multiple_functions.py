#import packages
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from copy import deepcopy
from datetime import datetime

class Scraper:
    def __init__(self, league, season):
        self.league = league
        self.season = season
    
    def scrape_site(self):
        #Header to be used in request on site
        headers = {'User-Agent':  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'}

        #Get structure of page
        page = f"https://www.transfermarkt.co.uk/{self.league}/spieltag/wettbewerb/IR1/plus/?saison_id={self.season}&spieltag=1"
        pageTree = requests.get(page, headers=headers)
        pageSoup = BeautifulSoup(pageTree.content, 'html.parser')

        #Find all matchdays in a given season (varies depending on League and Season combination)
        md_scrape = list(filter(None,pageSoup.find_all("div",{"class": "inline-select"})[1].text.split('\n')))

        #md_scrape returns a String, like "1.Matchday", we want to strip away the unnecessary text
        matchdays = []

        for i in range(len(md_scrape)):
            matchdays.append(''.join(ch for ch in md_scrape[i] if ch.isdigit()))

        self.matchday_data = []
        matchday_data = self.matchday_data

        #Now that we have all of the matchdays for the given League and Season combination, we want to pull all data for all seasons
        for i in range(len(matchdays)):
            page = f"https://www.transfermarkt.co.uk/{self.league}/spieltag/wettbewerb/IR1/plus/?saison_id={self.season}&spieltag={matchdays[i]}"
            pageTree = requests.get(page, headers=headers)
            pageSoup = BeautifulSoup(pageTree.content, 'html.parser')

            matchday_data.append(pageSoup)
        
        scrape_result = [matchdays, matchday_data]
        return scrape_result
    
    def extract_teams_result(self, matchday_data):
        self.matchday_data = matchday_data

        #Find the home teams, and append to their own list
        home_team = []

        for i in range(len(matchday_data)):
            home_team.append(matchday_data[i].find_all("td",
                            {"class": "rechts hauptlink no-border-rechts hide-for-small spieltagsansicht-vereinsname"}))
            
        for i in range(len(home_team)):
            for j in range(len(home_team[i])):
                home_team[i][j] = re.split(r'\t+',home_team[i][j].text)
                
                if(len(home_team[i][j]) == 1):
                    home_team[i][j].insert(0,'')
            
                home_team[i][j] = home_team[i][j][1].strip()

        #Find the away teams, and append to their own list
        away_team = []

        for i in range(len(matchday_data)):
            away_team.append(matchday_data[i].find_all("td",
                            {"class": "hauptlink no-border-links no-border-rechts hide-for-small spieltagsansicht-vereinsname"}))
            
        for i in range(len(away_team)):
            for j in range(len(away_team[i])):
                away_team[i][j] = re.split(r'\t+', away_team[i][j].text.rstrip('\t'))[0].strip()

        #Find match results, and append to their own list
        result = []

        for i in range(len(matchday_data)):
            result.append(matchday_data[i].find_all("span",{"class": "matchresult finished"}))
            
        for i in range(len(result)):
            for j in range(len(result[i])):
                result[i][j] = result[i][j].text.replace(':', '-')

        results_data = [home_team, away_team, result]
        return results_data

    def extract_match_info(self, matchday_data):
        #Find additional match info, and append to list
        match_info = []

        for i in range(len(matchday_data)):
            match_info.append(matchday_data[i].find_all("td",{"class": "zentriert no-border"}))   

        for i in range(len(match_info)):

            for j in range(0, len(match_info[i]), 2):

                if(type(match_info[i][j]) == str):
                    match_info[i][j] = match_info[i][j]

                else:
                    if(any(char.isdigit() for char in match_info[i][j].text) == True):
                        match_info[i][j] = match_info[i][j].text.strip().split("\n")[1].strip()

        #Extract match dates           
        self.dates = []
        dates = self.dates

        for i in range(len(match_info)):
            dates.append(match_info[i][::2])
            
        """
        Things get a little tricky (and messy) here. 

        Formatting is a little awkward when it comes to attendances and referees, due to missing data points.

        There is definitely room for improvement here.
        """

        attendance_referee = []

        for i in range(len(match_info)):
            attendance_referee.append(match_info[i][1::2])

        for i in range(len(attendance_referee)):
            for j in range(len(attendance_referee[i])):
                attendance_referee[i][j] = attendance_referee[i][j].text

        for i in range(len(attendance_referee)):
            for j in range(len(attendance_referee[i])):
                attendance_referee[i][j] = attendance_referee[i][j].split()

        for i in range(len(attendance_referee)):
            for j in range(len(attendance_referee[i])):
                if(len(attendance_referee[i][j]) == 2):
                    attendance_referee[i][j].insert(0, '')
                    attendance_referee[i][j].insert(1, '')
                
                if(len(attendance_referee[i][j]) == 6):
                    attendance_referee[i][j].remove('sold')
                    attendance_referee[i][j].remove('out')
                    
        self.attendance = deepcopy(attendance_referee)
        attendance = self.attendance

        for i in range(len(attendance)):
            for j in range(len(attendance[i])):
                attendance[i][j] = attendance[i][j][0].replace('.', ',')

                
        self.referee = deepcopy(attendance_referee)
        referee = self.referee

        referee[0][0][2:4] = [' '.join(referee[0][0][2:4])]

        for i in range(len(referee)):
            for j in range(len(referee[i])):
                referee[i][j] = [' '.join(referee[i][j][2:4])]
                referee[i][j] =  referee[i][j][0]
        
        match_data = [dates, attendance, referee]
        return match_data
    
    def write_to_df(self, scrape_result, results_data, match_data, season):
        #Write data to DataFrame
        df = pd.DataFrame({"Matchday": scrape_result, "Home": results_data[0], "Away": results_data[1], "Result":results_data[2], 
                           "Attendance": match_data[0], "Date": match_data[1], "Referee": match_data[2]})

        df['Matchday'] = df['Matchday'].astype(int)

        df = df.set_index('Matchday').apply(lambda x: x.apply(pd.Series).stack()).reset_index()
        df = df.drop('level_1', axis = 1).sort_values(by=['Matchday'])

        df['Season'] = int(season)+1

        return df
    
def main():
    league = 'sse-airtricity-league-premier-division'
    season = 2021

    loi_2021 = Scraper(league, season)

    startTime = datetime.now()

    scraper = loi_2021.scrape_site()
    matchday_results = loi_2021.extract_teams_result(scraper[1])

    match_info = loi_2021.extract_match_info(scraper[1])

    resultant_df = loi_2021.write_to_df(scraper[0], matchday_results, match_info, season)
    
    print("Script using class and multiple functions takes %s minutes" % (datetime.now() - startTime))

    resultant_df.to_csv(".csv", index = False)

if __name__ == "__main__":
    main()