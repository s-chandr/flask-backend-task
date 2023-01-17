import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask,request,render_template
import json
CREATE_USER_TABLE = ( " CREATE TABLE IF NOT EXISTS USERS(id SERIAL PRIMARY KEY , name TEXT); ")
INSERT_USER_TABLE = ( " INSERT INTO USERS(name) VALUES(%s) RETURNING id ;")

CREATE_MESSAGE_TABLE = ( """ CREATE TABLE IF NOT EXISTS MESSAGES
(user_id INTEGER , id SERIAL PRIMARY KEY , message TEXT ,
time_posted TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP , 
likes INTEGER DEFAULT 0 , FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE ) ; """)
INSERT_MESSAGE_TABLE = (" INSERT INTO MESSAGES(user_id , message) VALUES (%s , %s) RETURNING id ; ")

CREATE_LIKES_TABLE = ( """ CREATE TABLE IF NOT EXISTS LIKES
(id SERIAL PRIMARY KEY , message_id INTEGER , user_id INTEGER, 
FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
""" )
INSERT_LIKES = (" INSERT INTO LIKES(message_id , user_id ) Values (%s,%s) RETURNING id ; ")
DELETE_LIKES = (" DELETE FROM LIKES WHERE message_id = %s AND user_id = %s; ")
CHECK = ("SELECT * from LIKES WHERE message_id = %s AND user_id = %s ; ") #error

#when first time execute code set it to false
execute_once = True

ADD_LIKES_TRIGGER = ("""CREATE OR REPLACE FUNCTION increase_like()
RETURNS TRIGGER AS
$$
BEGIN 
UPDATE MESSAGES
SET likes = (SELECT likes from MESSAGES where id = NEW.message_id ) + 1
WHERE MESSAGES.id = NEW.message_id ;
return new ;
END;
$$ 
language 'plpgsql';

CREATE TRIGGER IF NOT EXISTS update_likes
AFTER INSERT ON likes
FOR EACH ROW 
EXECUTE PROCEDURE increase_like();
""" )
 
REMOVE_LIKES_TRIGGER= ("""CREATE OR REPLACE FUNCTION decrease_like()
RETURNS TRIGGER AS
$$
BEGIN 
UPDATE MESSAGES
SET likes = (SELECT likes from MESSAGES where id = old.message_id ) - 1
WHERE MESSAGES.id = old.message_id ;
return new ;
END;
$$ 
language 'plpgsql';

CREATE TRIGGER IF NOT EXISTS update_downvote
AFTER DELETE ON likes
FOR EACH ROW 
EXECUTE PROCEDURE decrease_like();
""" )
load_dotenv()  # loads variables from .env file into environment

app = Flask(__name__)
url = os.environ.get("DATABASE_URL")  # gets variables from environment
connection = psycopg2.connect(url)


#add user to user table
@app.post("/add/user")
def create_user():
    data = request.get_json()
    user_name = data["user_id"]
    # user_name = str(request.form['uname'])
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_USER_TABLE)
            cursor.execute(INSERT_USER_TABLE,(user_name,))
            user_id = cursor.fetchone()[0]
    return f"{user_id} created",201

#See all messages with total likes
@app.get("/messages")
def get_messages():
    with connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * from MESSAGES ORDER BY time_posted DESC;")
            rows = cursor.fetchall()
            print("user_id  message_id  message_text time_posted likes" )
            for row in rows:
                print(row)
            return rows

#add message to message table
@app.post("/add/message")
def create_message():
    data = request.get_json()
    user_id = data["user_id"]
    message = data["message"]
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_MESSAGE_TABLE)
            cursor.execute(INSERT_MESSAGE_TABLE,(user_id, message,))
            message_id = cursor.fetchone()[0]
    return f"{message} created with {message_id}",201

#like message 
@app.post("/like")
def add_like():
    data = request.get_json()
    message_id = data["message_id"]
    user_id = data["user_id"]
    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_LIKES_TABLE)
            if( not execute_once):
                cursor.execute(ADD_LIKES_TRIGGER)
                cursor.execute(REMOVE_LIKES_TRIGGER)

            try : 
                cursor.execute(CHECK ,(message_id, user_id,) )
                print(cursor.fetchone()[0])
                return "you have already liked once" , 202
            except : 
                cursor.execute(INSERT_LIKES,(message_id, user_id,))
                like_id = cursor.fetchone()[0]
                return f"{user_id} has liked {message_id}  and likeid id {like_id}",201
                 
            
#dislike message
@app.post("/dislike")
def dislike():
    data = request.get_json()
    message_id = data["message_id"]
    user_id = data["user_id"]
    with connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(DELETE_LIKES,(message_id, user_id,))
                return "disliked",201
            except:
                return "Invalid/No more disliking than once"

            
            
    



if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.run(debug=True,port=8000)