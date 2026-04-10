**Study Routine Tracker URL: **[Link Text](https://com)


pip install -r requirements.txt
streamlit run app.py

net start postgresql-x64-18

python -m streamlit run app.py
python -m py_compile app.py

python -m streamlit run app.py --server.headless true











create a daily tracker using python for my routine. For a day with date and time in Indian standard time, there are predefined box (office, revision, testpaper revision, coaching, test, wfh, study, dinner, lunch, breakfast etc). there is search menu for searching for these predefined boxes and if it is not there you can create it and can use it from next time. within these box there are further predefined sub-boxes open up if you select them like for study, there are custom subboxes which require subject, chapter no and duration of study. similarly entertainment contain predefined sub-boxes of movie (which further contain sub box of outside and room), sports, cricket match, went outside. similarly for social media, there are custom boxes for insta and youtube (which further contain subbox of study and random videos). for each boxes at the last subbox or box, there is duration box is present for all using which we track how much time i have spend for that activity. there is option of time input too in form of 12 hour format AM/PM dropdown(PM by default). the time duration if given by user, should be in decimal or integer and have dropdown of hr and min (hr by default). it also contain the option of predefined swiggy/zomato/outside box which has subbox of price only for tracking money spend. Similarly there is also boxof uber/ola/rapido which also contain only price. similarly for friend split with custom activity. It also contain monthly calender with date and also yearly calender in which all the month with date appear. for these month and year calender each date  is indicated by colors like red, black, green, golden, yellow based on the time spend for study. if less than 1 hr study= black, red=for weekend <5hr and for  weekday <3hr, yellow = for weekend <8hr and weekday <6hr, green= for weekday <8hr and for weekend <14 hr and golden= for weekday <11.5hr and for weekend <17.5hr. this month and yearly activity is directly connected with daily input and update automatically as we save a day activity. the weekend and weekday is depend on the condition of if that day any boxes of office, wfh, test or coaching is there. test day is marked with pink color. also using the input of dates by user, prepare the tabular targets, deadline and time taken to complete the subject and its chapters, test paper revision. revision completed, etc. also there is target page where we can write the daily, custom days, weekly, fortnightly, monthly and custom months targets which is later match with the target meet or achieved and provide us the analysis using tabular and graphically. also it give the weekly, monthly and yearly expense analysis.

use groq api key for ai related interpretation if required and use database for storing all these data. beautify the UI for it