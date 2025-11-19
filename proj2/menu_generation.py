import os
import pandas as pd
import datetime
import time
import json
import random
import re
from typing import Tuple, List

import proj2.llm_toolkit as llm_toolkit
from proj2.sqlQueries import *

db_file = os.path.join(os.path.dirname(__file__), "CSC510_DB.db")

## LLM error handling
MAX_LLM_TRIES = 3
LLM_ATTRIBUTE_ERROR = -1

## Increase to increase the sample size the AI can draw from at the cost of increased runtime
ITEM_CHOICES = 10

## Days of the week in an array - should be the same as in the database*
DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

## LLM Prompt - defined as global variables to enable testing
SYSTEM_TEMPLATE = "You are a health and nutrition expert planning meals for a customer based on their preferences. Use only the menu items provided under CSV CONTEXT."
PROMPT_TEMPLATE = """Choose a meal for a customer based on their preferences: {preferences}
Make sure that the item makes sense for {meal}.
Provide only the itm_id as output

CSV CONTEXT:
{context}"""

## Regex used for parsing a number from LLM Output
LLM_OUTPUT_MATCH = r"<\|start_of_role\|>assistant<\|end_of_role\|>(\d+)<\|end_of_text\|>"

## Preset Meal times - In the future, times will be user-provided
BREAKFAST_TIME = 1000
LUNCH_TIME = 1400
DINNER_TIME = 2000


def get_meal_and_order_time(meal_number: int) -> Tuple[str, int]:
    """
    Maps a meal number to it's cooresponding meal as a string as well as its cooreponding meal time

    Args:
        meal_number (int): The meal number to get the meal and order times for

    Returns:
        str: The name of the meal as a string ("breakfast", "lunch", or "dinner")
        int: The time the meal is typically ordered at in HHMM format (in 24H time)

    Raises:
        ValueError: if meal_number is not 1, 2, or 3
    """
    meal = ""
    order_time = -1
    match meal_number:
        case 1:
            meal = "breakfast"
            order_time = BREAKFAST_TIME
        case 2:
            meal = "lunch"
            order_time = LUNCH_TIME
        case 3:
            meal = "dinner"
            order_time = DINNER_TIME
        case _:
            raise ValueError("The meal number must be 1, 2, or 3")
    return meal, order_time


def get_weekday_and_increment(date: str) -> Tuple[str, str]:
    """
    Converts a date string in YYYY-MM-DD format to the corresponding day of the week and returns the next date

    Args:
        date (str): The date string in YYYY-MM-DD format

    Returns:
        str: The next day, in YYYY-MM-DD format
        str: The corresponding day of the week ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

    Raises:
        ValueError: if the date string is not in the correct format (YYYY-MM-DD) or is invalid
    """
    year, month, day = map(int, date.split("-"))
    try:
        date = datetime.datetime(year, month, day)
    except:
        raise ValueError(
            "Unable to parse date string. Ensure it is formatted properly as to YYYY-MM-DD format"
        )
    next_day = date + datetime.timedelta(days=1)
    return next_day.strftime(r"%Y-%m-%d"), DAYS_OF_WEEK[date.weekday()]


def format_llm_output(output: str) -> int:
    """
    Grabs the LLM output and extracts the item ID from it

    Args:
        output (str): The output from the llm_toolkit LLM

    Returns:
        int: The item ID extracted from the LLM output

    Raises:
        ValueError: if the LLM output does not match the expected format or if multiple matches are found
    """
    match = LLM_OUTPUT_MATCH
    result = 0
    try:
        result = int(re.search(match, output).group(1))
    except AttributeError:
        return LLM_ATTRIBUTE_ERROR
    try:
        print(re.search(match, output).group(2))
        raise ValueError(
            "Injection attack may have gotten through. There should not be multiple matches for LLM output."
        )
    except Exception:
        None
    return result


def limit_scope(items: pd.DataFrame, num_choices: int) -> List[int]:
    """
    Limits the number of items to ITEM_CHOICES by randomly selecting items if necessary

    Args:
        items (pd.DataFrame): The DataFrame containing the items
        num_choices (int): The maximum number of choices to return

    Returns:
        List[int]: The list of item_ids of the selected items
    """
    num_items = items.shape[0]
    choices = range(num_items)
    if num_items > num_choices:
        choices = random.sample(choices, num_choices)
    return choices


def filter_allergens(menu_items: pd.DataFrame, allergens: str) -> pd.DataFrame:
    """
    Filters out menu items that contain any of the specified allergens from the provided DataFrame

    Args:
        menu_items (pd.DataFrame): The DataFrame containing the menu items
        allergens (str): A comma-separated string of allergens to filter out

    Returns:
        pd.DataFrame: The filtered DataFrame with menu items containing the specified allergens removed
    """
    for index, rows in menu_items.iterrows():
        if rows["allergens"] is not None:
            item_allergens = rows["allergens"].split(",")
            if any(allergen in item_allergens for allergen in allergens.split(",")):
                menu_items.drop(index, inplace=True)
    return menu_items


def filter_closed_restaurants(restaurant: pd.DataFrame, weekday: str, time: int) -> pd.DataFrame:
    """
    Filters out restaurants that are closed at the specified time on the specified weekday

    Args:
        restaurant (pd.DataFrame): The DataFrame containing the restaurant data
        weekday (str): The day of the week to check (e.g., "Mon", "Tue", etc.)
        time (int): The time to check in HHMM format (24H time)

    Returns:
        pd.DataFrame: The filtered DataFrame with closed restaurants removed
    """
    for index, rows in restaurant.iterrows():
        opening_times = json.loads(rows["hours"])[weekday]
        if len(opening_times) % 2 == 1:
            print("Odd opening times - cannot process")
            restaurant = restaurant[restaurant["rtr_id"] != rows["rtr_id"]]
        elif len(opening_times) >= 2:
            open = False
            for x in range(int(len(opening_times) / 2)):
                if opening_times[x * 2] <= time and opening_times[x * 2 + 1] >= time:
                    open = True
            if not open:
                restaurant = restaurant[restaurant["rtr_id"] != rows["rtr_id"]]
        else:
            restaurant = restaurant[restaurant["rtr_id"] != rows["rtr_id"]]
    return restaurant


class MenuGenerator:
    """
    MenuGenerator class that uses an LLM to generate menu items based on user preferences and restrictions
    """

    def __init__(self, tokens: int = 500):
        """
        Initializes the MenuGenerator with menu items and restaurants from the database and initializes
        the local LLM.

        Args:
            tokens (int): The number of tokens to use for the LLM generation
        """
        conn = create_connection(db_file)
        self.menu_items = pd.read_sql_query("SELECT * FROM MenuItem WHERE instock == 1", conn)
        self.restaurants = pd.read_sql_query(
            'SELECT rtr_id, hours FROM Restaurant WHERE status=="Open"', conn
        )
        close_connection(conn)

        self.generator = llm_toolkit.LLM(tokens=tokens)

    def __get_context(self, allergens: str, weekday: str, order_time: int, num_choices: int) -> str:
        """
        Generates the context block for the LLM based on the provided allergens, date, and order time

        Args:
            allergens (str): A comma-separated string of allergens to filter out
            weekday (str): The day of the week (e.g., "Mon", "Tue", etc.)
            order_time (int): The time the meal is typically ordered at in HHMM format (in 24H time)
            num_choices (int): The maximum number of choices to provide in the context
            item_ids (List[int]): The list of item_ids passed - used for checking validity

        Returns:
            str: The context block for the LLM in CSV format
        """
        start = time.time()

        combined = pd.merge(self.menu_items, self.restaurants, on="rtr_id", how="left")

        ## Removes restaurants that are closed during the order time
        combined = filter_closed_restaurants(combined, weekday, order_time)

        ## Removes items that contain allergens
        combined = filter_allergens(combined, allergens)

        ## Randomly selects ITEM_CHOICES number of items to present to the LLM
        choices = limit_scope(combined, num_choices)

        context_data = "item_id,name,description,price,calories\n"

        ## Create the context data with the chosen items
        item_ids = []
        for x in choices:
            row = combined.iloc[x]
            context_data += f"{row['itm_id']},{row['name']},{row['description']},{row['price']},{row['calories']}\n"
            item_ids.append(row["itm_id"])

        end = time.time()
        print("Context block generated in %.4f seconds" % (end - start))
        return context_data, item_ids

    def __pick_menu_item(
        self, preferences: str, allergens: str, weekday: str, meal_number: int
    ) -> int:
        """
        Picks a menu item based on user preferences, allergens, date, and meal number

        Args:
            preferences (str): A comma-separated string of user preferences
            allergens (str): A comma-separated string of allergens to filter out
            weekday (str): The day of the week (e.g., "Mon", "Tue", etc.)
            meal_number (int): The meal number (1 for breakfast, 2 for lunch, 3 for dinner)

        Returns:
            int: The item_id of the selected menu item
        """
        meal, order_time = get_meal_and_order_time(meal_number)

        num_choices = ITEM_CHOICES

        ## Tries to get output from LLM a number of times, increasing the number of options every time
        for x in range(MAX_LLM_TRIES):
            context, item_ids = self.__get_context(allergens, weekday, order_time, num_choices)

            ## Gets the prompt
            system = SYSTEM_TEMPLATE
            prompt = PROMPT_TEMPLATE

            ## Initializes variables in prompt
            prompt = prompt.replace("{preferences}", preferences)
            prompt = prompt.replace("{context}", context)
            prompt = prompt.replace("{meal}", meal)

            llm_output = self.generator.generate(system, prompt)
            output = format_llm_output(llm_output)
            if output > 0 and output in item_ids:
                return output
            ## If failed, try increasing the number of choices
            num_choices += ITEM_CHOICES
        raise RuntimeError(
            f"""LLM has failed {MAX_LLM_TRIES} times to generate a meal. This may be a critical error, a lack of options, or a bad prompt. 
LLM output:
{llm_output}"""
        )

    def update_menu(
        self,
        menu: str,
        preferences: str,
        allergens: str,
        date: str,
        meal_numbers: List[int],
        number_of_days: int = 1,
    ) -> str:
        """
        Updates the menu string with a new menu item based on user preferences, allergens, date, and meal number

        Args:
            menu (str): The current menu string (can be empty or None)
            preferences (str): A comma-separated string of user preferences
            allergens (str): A comma-separated string of allergens to avoid
            date (str): The date string in YYYY-MM-DD format
            meal_number (List[int]): The list of meal numbers to generate (1 for breakfast, 2 for lunch, 3 for dinner). e.g. [1,2,3]
            number_of_days (int): The number of days to generate meals for, past the {date} specified

        Returns:
            str: The updated menu string
        """
        next_date, current_weekday = get_weekday_and_increment(date)
        for x in range(number_of_days):
            for meal_number in meal_numbers:
                if menu is None or len(menu) < 1:
                    itm_id = self.__pick_menu_item(
                        preferences, allergens, current_weekday, meal_number
                    )
                    menu = f"[{date},{itm_id},{meal_number}]"
                elif re.search(rf"\[{date},\d+,{meal_number}\]", menu) is None:
                    print(rf"\[{date},\d+,{meal_number}\]")
                    print(menu)
                    itm_id = self.__pick_menu_item(
                        preferences, allergens, current_weekday, meal_number
                    )
                    menu = f"{menu},[{date},{itm_id},{meal_number}]"
            date = next_date
            next_date, current_weekday = get_weekday_and_increment(date)
        return menu
