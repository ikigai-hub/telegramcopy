import os
import asyncio
from pyrogram import Client
from dotenv import load_dotenv


class SessionManager:
    def __init__(self, workdir='sessions'):
        load_dotenv()

        self.api_id = os.getenv('TELEGRAM_API_ID')
        self.api_hash = os.getenv('TELEGRAM_API_HASH')
        self.workdir = workdir

    def parse_sessions(self):
        sessions = []
        for file in os.listdir(self.workdir):
            if file.endswith(".session"):
                sessions.append(file.replace(".session", ""))

        print(f"Found {len(sessions)} session files!")
        return sessions

    def get_first_session(self):
        sessions = self.parse_sessions()

        if not sessions:
            raise ValueError("No session files found")

        return sessions[0]


def create_client(session_name):
    session_manager = SessionManager()
    return Client(
        name=session_name,
        api_id=session_manager.api_id,
        api_hash=session_manager.api_hash,
        workdir=session_manager.workdir
    )


async def send_message(client, message_text, target_username='mcqueen_bonkbot'):
    try:
        sent_message = await client.send_message(
            chat_id=target_username,
            text=message_text
        )
        print(f"Contract Address sent successfully to Bonkbot")
        return sent_message.id

    except Exception as e:
        print(f"Error sending message: {e}")


async def reply_message(client, message_text, message_id, target_username='mcqueen_bonkbot'):
    try:
        sent_message = await client.send_message(
            chat_id=target_username,
            text=message_text,
            reply_to_message_id=message_id
        )
        print(f"Coin buy message sent successfully to Bonkbot")
        return sent_message.id

    except Exception as e:
        print(f"Error sending reply message: {e}")


async def print_received_message(client, bot_username='mcqueen_bonkbot'):
    try:
        async for message in client.get_chat_history(bot_username, limit=1):
            print(f"Last message from {bot_username}: {message.text}")

    except Exception as e:
        print(f"Error fetching the bot's reply: {e}")



async def interact_with_button(client, button_text, bot_username='mcqueen_bonkbot'):
    try:
        async for message in client.get_chat_history(bot_username, limit=1):
            if hasattr(message, 'reply_markup') and message.reply_markup:
                for row in message.reply_markup.inline_keyboard:
                    for button in row:
                        if button.text == button_text:
                            result = await client.request_callback_answer(
                                chat_id=bot_username,
                                message_id=message.id,
                                callback_data=button.callback_data
                            )

                            print(f"{button_text} button clicked successfully!")
                            return result
            break

    except Exception as e:
        print(f"Error clicking {button_text} button: {e}")


async def wait_for_bot_response(client, bot_username='mcqueen_bonkbot', timeout=1, target_text="Reply with the amount you wish to buy", retries=3):
    try:
        for _ in range(retries):
            async for message in client.get_chat_history(bot_username, limit=1):
                if message.from_user and message.from_user.is_bot and target_text in message.text:
                    return message.id

            print(f"Bot hasn't responded yet, retrying in {timeout} seconds...")
            await asyncio.sleep(timeout) 

        print(f"No bot response found containing '{target_text}' within {retries} attempts.")
        return None

    except Exception as e:
        print(f"Error waiting for bot's response: {e}")
        return None


async def buy_coin(client, contract_address):
    try:
        message_text = f"/start=ref_ibayi_ca_{contract_address}"
        await send_message(client, message_text)

        await asyncio.sleep(0.4)

        # Click "Buy X SOL" button
        button_result = await interact_with_button(client, "Buy X SOL")
        
        if button_result is not None:
            print("Waiting for BonkBot response...")
            bot_response_message_id = await wait_for_bot_response(client)

            if bot_response_message_id is not None:
                sol_amount = float(os.getenv("SOL_AMOUNT", "0"))
                if sol_amount <= 0:
                   print("SOL_AMOUNT must be greater than 0.")
                   return
                
                message_text = str(sol_amount)
                print(f"Buying coin with {sol_amount} SOL")
                await reply_message(client, message_text, bot_response_message_id)

                await asyncio.sleep(7)

                SET_LIMIT_ORDER = os.getenv("SET_LIMIT_ORDER", "False").lower() == "true"
                try:
                    PERCENT_COINS_LIMIT_SELL = int(os.getenv("PERCENT_COINS_LIMIT_SELL", "100"))
                    MULTIPLE_CHANGE_LIMIT_SELL = float(os.getenv("MULTIPLE_CHANGE_LIMIT_SELL", "1"))
                    if MULTIPLE_CHANGE_LIMIT_SELL < 0:
                        raise ValueError("Limit sell percentage must be a number between 0")
                except ValueError as e:
                    print(f"Invalid percentage value for limit order: {e}")
                    return
               
                if SET_LIMIT_ORDER:
                   check_order_message = await wait_for_bot_response(client, target_text="Profit")
                   if check_order_message is not None:
                       await interact_with_button(client, "Limit")
                       await asyncio.sleep(2)
                       await interact_with_button(client, "Limit Sell X %")
                       await asyncio.sleep(2)
                       check_first_limit_message = await wait_for_bot_response(client, target_text="Reply with the % you wish to limit sell")
                       if check_first_limit_message is not None:
                          percent_coins_limit_sell = f'{PERCENT_COINS_LIMIT_SELL}%'
                          message_text = percent_coins_limit_sell
                          await reply_message(client, message_text, check_first_limit_message)
                          await asyncio.sleep(2)
                          check_second_limit_message = await wait_for_bot_response(client, target_text="Enter a trigger")
                          if check_second_limit_message is not None:
                             multiple_change_limit_sell = f'{MULTIPLE_CHANGE_LIMIT_SELL}x'
                             message_text = multiple_change_limit_sell
                             await reply_message(client, message_text, check_second_limit_message)
                             await asyncio.sleep(2)
                             check_limit_confirm_message = await wait_for_bot_response(client, target_text="Take Profit Sell")
                             if check_limit_confirm_message is not None:
                                await interact_with_button(client, "Confirm")
                                await asyncio.sleep(2)
                                check_limit_success_message = await wait_for_bot_response(client, target_text="successfully placed")
                                if check_limit_success_message is not None:
                                    print("Limit order successfully placed")

                # i only use it for testing 
                # await print_received_message(client)
            else:
                print("Failed to find the bot's response message.")

    except Exception as e:
        print(f"Error in buy_coin: {e}")


if __name__ == "__main__":
    pass
