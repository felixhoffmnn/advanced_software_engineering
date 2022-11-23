import datetime
import json
import os
import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from sys import platform

import pandas as pd
from fire import Fire
from loguru import logger
from pandas.errors import IndexingError

from aswe.core.use_case import GeneralUseCase
from aswe.core.user_interaction import SpeechToText, TextToSpeech


def clear_shell() -> None:
    """Clears any previous text in the shell"""
    if platform == "linux" or platform == "linux2" or platform == "darwin":
        os.system("clear")
    elif platform == "win32":
        os.system("cls")


@dataclass
class User:
    """Dataclass supposed to store the user data

    * TODO: Add more attributes and evaluate the existing ones

    Parameters
    ----------
    name : str | None, optional
        The name of the user. _By default `None`_.
    age : int | None, optional
        The age of the user. _By default `None`_.
    street : str | None, optional
        The street of the user. _By default `None`_.
    city : str | None, optional
        The city of the user. _By default `None`_.
    zip_code : int | None, optional
        The zip code of the user. _By default `None`_.
    country : str | None, optional
        The country of the user. _By default `None`_.
    """

    name: str | None = None
    age: int | None = None
    street: str | None = None
    city: str | None = None
    zip_code: int | None = None
    country: str | None = None


class Agent:
    """Class to handle speech to text conversion and text to speech conversion"""

    def __init__(self, get_mic: bool = False, get_user: bool = False) -> None:
        """Initialize the agent which handles all the core functionality like speech to text and text to
        speech conversion but also the calculation of the best matching use case for the parsed text.

        * TODO: Reevaluate naming for `self.tts.convert_text` and `self.stt.convert_speech`

        Parameters
        ----------
        get_mic : bool, optional
            Boolean if the speech to text class should first ask for the microphone to use. _By default `False`_.
        get_user : bool, optional
            Boolean if the default user should be used. _By default `False`_.
        """
        try:
            with open(Path("data/quotes.json"), encoding="utf-8") as file:
                self.quotes = (
                    pd.DataFrame(
                        [
                            [use_case, choice, phrase]
                            for use_case, value in json.load(file).items()
                            for choice, phrase in value.items()
                        ],
                        columns=["use_case", "choice", "phrase"],
                    )
                    .explode("phrase")
                    .reset_index(drop=True)
                )
        except OSError:
            logger.error("Could not open file. Please check if the file exists.")
            sys.exit(1)

        self.stt = SpeechToText(get_mic)
        self.tts = TextToSpeech()

        self.assistant_name = "Marcell J'Avais"
        if get_user:
            self.user = self._get_user()
        else:
            self.user = User(
                name="Marcell", age=23, street="Hauptstraße 1", city="Berlin", zip_code=12345, country="Germany"
            )

        self.uc_general = GeneralUseCase(self.stt, self.tts, self.assistant_name)

        print(self.user.name)

    def _greeting(self) -> None:
        """Function to greet the user."""
        hour = datetime.datetime.now().hour

        if 4 <= hour < 12:
            greeting_text = "Good Morning."
        elif 12 <= hour < 18:
            greeting_text = "Good Afternoon."
        else:
            greeting_text = "Good Evening."

        self.tts.convert_text(greeting_text)
        self.tts.convert_text(f"I am your Assistant {self.assistant_name}")

    def _get_user(self) -> User:
        """Asks for the name of the user.

        * TODO: Refactor into a util function
        """
        self.tts.convert_text("What should i call you?")

        username = None
        while username is None:
            print("")
            username = self.stt.convert_speech()
            if username is None:
                self.tts.convert_text("Sorry, I didn't get that. Please say that again.")

        self.tts.convert_text(f"Hello {username}")  # type: ignore
        self.tts.convert_text("How can I help you?")

        return User(name=username)

    def get_best_match(self, text: str) -> tuple[str, str] | None:
        """Find the best match for the parsed text

        Parameters
        ----------
        text : str
            The parsed text which should be matched to a use case

        Returns
        -------
        tuple[str, str]
            Returns a tuple with the use case and the selected endpoint within the use case (choice)
        """
        logger.debug(f"Finding the best match for the parsed text: {text}")
        logger.debug(f"The data frame contains {len(self.quotes)} rows")
        temp_df: pd.DataFrame = self.quotes.copy()

        try:
            temp_df["similarity"] = temp_df["phrase"].apply(
                lambda value: SequenceMatcher(None, text, value).quick_ratio()
            )
            temp_df = temp_df.iloc[
                temp_df.groupby(["use_case", "choice"], sort=False)["similarity"].agg(pd.Series.idxmax)
            ]
            temp_df = temp_df[temp_df["similarity"] >= 0.5].reset_index(drop=True)
            temp_df = temp_df.loc[temp_df["similarity"] == temp_df["similarity"].max()]
        except ValueError:
            logger.warning("Could not find a match for the parsed text meeting the requirements.")
            return None
        except (KeyError, IndexingError):
            logger.error("The data frame does not match the required schema.")
            return None

        if temp_df.empty:
            return None

        choice = 0
        if len(temp_df) > 1:
            print("")
            self.tts.convert_text("I got multiple matches. Please choose one.")
            print("")
            for index, row in temp_df.iterrows():
                print(f"{index + 1}: {row['use_case']}, {row['choice']}")  # type: ignore
            print("")
            while choice == 0:
                try:
                    choice = int(input("Please enter the number of your choice: "))
                except ValueError:
                    self.tts.convert_text("Sorry, I didn't get that. Please try again.")

        selected_row = temp_df.iloc[choice - 1 if len(temp_df) > 1 else 0]
        return (selected_row["use_case"], selected_row["choice"])

    def agent(self) -> None:
        """Main function to interact with the user

        * TODO: Get user data by console or attributes
        """
        clear_shell()
        self._greeting()
        self._get_user()

        while True:
            print("")
            query = self.stt.convert_speech()
            if not query:
                self.tts.convert_text(
                    "Sorry, I was not able to parse anything. If you said something, please try again."
                )
                continue
            parsed_text = query.lower()
            self.evaluate_use_case(parsed_text)

    def evaluate_use_case(self, text: str) -> None:
        """Evaluates the parsed text to trigger the correct use case

        * TODO: Implement more use cases
        * TODO: Add method for calculating the similarity between the parsed text and the use case

        Parameters
        ----------
        text : str
            The voice input of the user parsed to lower case string
        """
        logger.debug(f"Evaluating the parsed text: {text}")

        df_best_match = self.get_best_match(text)
        if df_best_match is None:
            self.tts.convert_text("Sorry, I didn't find a match for your request.")
            return None

        if df_best_match[0] == "general":
            self.uc_general.trigger_assistant(df_best_match[1])
        elif df_best_match[0] == "morningBriefing":
            raise NotImplementedError
        elif df_best_match[0] == "events":
            raise NotImplementedError
        elif df_best_match[0] == "transportation":
            raise NotImplementedError
        elif df_best_match[0] == "sport":
            raise NotImplementedError
        else:
            self.tts.convert_text(
                "I was not able to map your input to a use case. Maybe the request is not implemented yet."
            )


if __name__ == "__main__":
    Fire(Agent)
