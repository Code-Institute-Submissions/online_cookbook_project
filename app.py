import os
from flask import (
        Flask, flash, render_template,
        redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)


@app.route("/")
@app.route("/get_recipes")
# gets a list of all recipes and lists them to the user
def get_recipes():
    recipes = list(mongo.db.recipes.find())
    return render_template("home.html", recipes=recipes)


@app.route("/home")
# Takes the user to the home screen
def home():
    recipes = list(mongo.db.recipes.find())
    return render_template("home.html", recipes=recipes)


@app.route("/search_recipe")
# allows the user to search for recipes in the database
def search_recipe():
    recipes = list(mongo.db.recipes.find())

    favourites = mongo.db.users.find_one(
        {"username": session["user"]})["favourites"]

    for favourite in favourites:
        recipe = mongo.db.recipes.find_one({"_id": ObjectId(favourite)})
        recipes.remove(recipe)

    return render_template("search_recipe.html", recipes=recipes)


@app.route("/search", methods=["GET", "POST"])
# the search function that searched the database for recipes matching input
def search():
    query = request.form.get("query")
    recipes = list(mongo.db.recipes.find({"$text": {"$search": query}}))

    favourites = mongo.db.users.find_one(
        {"username": session["user"]})["favourites"]

    for favourite in favourites:
        recipe = mongo.db.recipes.find_one({"_id": ObjectId(favourite)})
        recipes.remove(recipe)

    return render_template("recipes.html", recipes=recipes,)


@app.route("/register", methods=["GET", "POST"])
# allows the user to make an account for their cook book
def register():
    if request.method == "POST":
        # check if user is in database
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {  # registers user account and creates a favourites array
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "favourites": []
        }

        mongo.db.users.insert_one(register)

        # put the new user into session
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password is the same
            if check_password_hash(
             existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(request.form.get("username")))
                return redirect(url_for("profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesnt exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # grab the session user's username from db
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]

    favourites = mongo.db.users.find_one(
        {"username": session["user"]})["favourites"]

    favourite_recipes = []

    for favourite in favourites:
        recipe = mongo.db.recipes.find_one({"_id": ObjectId(favourite)})
        favourite_recipes.append(recipe)

    print(username)
    if session["user"]:
        recipes = list(mongo.db.recipes.find({'created_by': session['user']}))
        return render_template("profile.html", username=username, recipes=recipes, favourite_recipes=favourite_recipes)

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    # remove user from session
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_recipe", methods=["GET", "POST"])
# allows users to create their own recipes
def add_recipe():
    if request.method == "POST":
        recipe = {
            "meal_type": request.form.get("meal_type"),
            "recipe_name": request.form.get("recipe_name"),
            "cuisine": request.form.get("cuisine"),
            "ingredients": request.form.getlist("ingredients"),
            "required_tools": request.form.get("required_tools"),
            "preparation_steps": request.form.get("preparation_steps"),
            "created_by": session["user"]
        }
        mongo.db.recipes.insert_one(recipe)
        flash("Recipe successfully Added")
        return redirect(url_for("get_recipes"))

    meals = mongo.db.meals.find().sort("meal_type", 1)
    return render_template("add_recipe.html", meals=meals)


@app.route("/edit_recipe/<recipe_id>", methods=["GET", "POST"])
# allows users to edit recipes to their liking
def edit_recipe(recipe_id):
    if request.method == "POST":
        submit = {
            "meal_type": request.form.get("meal_type"),
            "recipe_name": request.form.get("recipe_name"),
            "cuisine": request.form.get("cuisine"),
            "ingredients": request.form.getlist("ingredients"),
            "required_tools": request.form.get("required_tools"),
            "preparation_steps": request.form.get("preparation_steps"),
            "created_by": session["user"]
        }
        mongo.db.recipes.update({"_id": ObjectId(recipe_id)}, submit)
        flash("Recipe successfully Updated")

    recipe = mongo.db.recipes.find_one({"_id": ObjectId(recipe_id)})
    meals = mongo.db.meals.find().sort("meal_type", 1)
    return render_template("edit_recipe.html", recipe=recipe, meals=meals)


@app.route("/delete_recipe/<recipe_id>")
# allows users to delete recipes
def delete_recipe(recipe_id):
    mongo.db.recipes.remove({"_id": ObjectId(recipe_id)})
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    mongo.db.users.update_one({"username": username}, {'$pull': {"favourites": ObjectId(recipe_id)}})
    flash("Recipe Successfully Deleted")
    return redirect(url_for("get_recipes"))


@app.route("/insert_recipe/<recipe_id>")
# lets users add recipes created by others to their own list
def insert_recipe(recipe_id):
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    mongo.db.users.update_one({"username": username}, {'$push': {"favourites": ObjectId(recipe_id)}})
    return redirect(url_for("search_recipe"))


# @app.route("/check_favourites/<recipe_id>")
# def check_favourites(recipe_id):
#     query = request.form.get("query")
#     recipes = list(mongo.db.users.find({"$text": {"$search": query}}))
#     mongo.db.users({"favourites": [ObjectId(recipe_id)]})


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)