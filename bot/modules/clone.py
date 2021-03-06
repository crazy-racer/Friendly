from random import SystemRandom
from string import ascii_letters, digits
from telegram.ext import CommandHandler
from telegram import InlineKeyboardMarkup,  
from threading import Thread
from time import sleep

from bot.helper.mirror_utils.upload_utils.gdriveTools import GoogleDriveHelper
from bot.helper.telegram_helper.message_utils import auto_delete_message, auto_delete_upload_message, sendMessage, sendMarkup, deleteMessage, delete_all_messages, update_all_messages, sendStatusMessage
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.mirror_utils.status_utils.clone_status import CloneStatus
from bot import dispatcher, LOGGER, STOP_DUPLICATE, AUTO_DELETE_UPLOAD_MESSAGE_DURATION, BOT_PM, CLONE_LIMIT, CHANNEL_USERNAME, MIRROR_LOGS, \
     download_dict, download_dict_lock, LINK_LOGS, FSUB, FSUB_CHANNEL_ID, Interval
from bot.helper.ext_utils.bot_utils import is_appdrive_link, is_gdrive_link, get_readable_file_size, new_thread


def _clone(message, bot, multi=0):
    if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1:
        reply_to = message.reply_to_message
        if reply_to is not None:
            try:
                reply_to.delete()
            except Exception as error:
                LOGGER.warning(error)
    uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
    if FSUB:
        try:
            user = bot.get_chat_member(f"{FSUB_CHANNEL_ID}", message.from_user.id)
            LOGGER.info(user.status)
            if user.status not in ("member", "creator", "administrator", "supergroup"):
                buttons = ButtonMaker()
                chat_u = CHANNEL_USERNAME.replace("@", "")
                buttons.buildbutton("šš» šššš”š”šš ššš”š šš»", f"https://t.me/{chat_u}")
                help_msg = f"šššš„ {uname},\nš¬š¢šØ š”ššš š§š¢ šš¢šš” š š¬ šššš”š”šš š§š¢ šØš¦š šš¢š§. \n\nššššš š¢š” š§šš šššš¢šŖ ššØš§š§š¢š” š§š¢ šš¢šš” šššš”š”šš"
                msg = sendMarkup(help_msg, bot, message, InlineKeyboardMarkup(buttons.build_menu(2)))
                Thread(target=auto_delete_upload_message, args=(bot, message, msg)).start()
                return
        except Exception:
            pass
    if BOT_PM and message.chat.type != "private":
        try:
            msg1 = f"šš±š±š²š± šš¼ššæ š„š²š¾šš²ššš²š± š¹š¶š»šø šš¼ š°š¹š¼š»š²\n"
            send = bot.sendMessage(message.from_user.id,text=msg1)
            send.delete()
        except Exception as e:
            LOGGER.warning(e)
            buttons = ButtonMaker()
            buttons.buildbutton('šš» š¦š§šš„š§ šš¢š§ šš»', f'https://t.me/{bot.get_me().username}?start=start')
            help_msg = f'šššš„ {uname},\nš¬š¢šØ š”ššš š§š¢ š¦š§šš„š§ š§šš šš¢š§ šØš¦šš”š š§š¢ šššš¢šŖ ššØš§š§š¢š”. \n\nšš§š¦ š”ššššš š¦š¢ šš¢š§ ššš” š¦šš”š š¬š¢šØš„ š šš„š„š¢š„/ššš¢š”š/ššššššš ššššš¦ šš” š£š . \n\nššššš š¢š” š§šš šššš¢šŖ ššØš§š§š¢š” š§š¢ š¦š§šš„š§ š§šš šš¢š§'
            reply_message = sendMarkup(help_msg, bot, message, InlineKeyboardMarkup(buttons.build_menu(2)))
            Thread(target=auto_delete_message, args=(bot, message, reply_message)).start()
            return
    args = message.text.split()
    reply_to = message.reply_to_message
    link = ''
    if len(args) > 1:
        link = args[1].strip()
        if link.strip().isdigit():
            multi = int(link)
            link = ''
        elif message.from_user.username:
            tag = f"@{message.from_user.username}"
        else:
            tag = message.from_user.mention_html(message.from_user.first_name)
    if reply_to:
        if len(link) == 0:
            link = reply_to.text.split(maxsplit=1)[0].strip()
        if reply_to.from_user.username:
            tag = f"@{reply_to.from_user.username}"
        else:
            tag = reply_to.from_user.mention_html(reply_to.from_user.first_name)
    if LINK_LOGS:
        if link != "":
            uname = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.first_name}</a>'
            slmsg = f'ā­āšŖ§ šš±š±š²š± šÆš ā¢ {uname}'
            slmsg += f'\nā°āšŖŖ šØšš²šæ šš ā¢ <code>{message.from_user.id}</code>\n\n'
            try:
                source_link = link
                for link_log in LINK_LOGS:
                    bot.sendMessage(link_log, text=slmsg + source_link, parse_mode=ParseMode.HTML)
            except IndexError:
                pass
            if reply_to is not None:
                try:
                    reply_text = reply_to.text
                    if is_url(reply_text):
                        source_link = reply_text.strip()
                        for link_log in LINK_LOGS:
                            bot.sendMessage(chat_id=link_log, text=slmsg + source_link, parse_mode=ParseMode.HTML)
                except TypeError:
                    pass
    is_appdrive = is_appdrive_link(link)
    if is_appdrive:
        try:
            msg = sendMessage(f"š£š„š¢ššš¦š¦šš”š šš£š£šš„šš©š ššš”š ā \n<code>{link}</code>", bot, message)
            link = appdrive(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            return sendMessage(str(e), bot, message)
    is_gdtot = is_gdtot_link(link)
    if is_gdtot:
        try:
            msg = sendMessage(f"ššššššššš ššššš šššš ā <code>{link}</code>", bot, message)
            link = gdtot(link)
            deleteMessage(bot, msg)
        except DirectDownloadLinkException as e:
            deleteMessage(bot, msg)
            return sendMessage(str(e), bot, message)

    if is_gdrive_link(link):
        gd = GoogleDriveHelper()
        res, size, name, files = gd.helper(link)
        if res != "":
            return sendMessage(res, bot, message)
        if STOP_DUPLICATE:
            LOGGER.info('Checking File/Folder if already in Drive...')
            smsg, button = gd.drive_list(name, True, True)
            if smsg:
                msg3 = "š šš¢š„š/ššØš„ššš« š¢š¬ šš„š«šššš² ššÆšš¢š„ššš„š š¢š§ šš«š¢šÆš.\n ššš«š šš«š š­š”š š¬ššš«šš” š«šš¬š®š„š­š¬ ā“:"
                return sendMarkup(msg3, bot, message, button)
        if CLONE_LIMIT is not None:
            LOGGER.info("Checking File/Folder Size...")
            if size > CLONE_LIMIT * 1024**3:
                msg2 = f"ššš¢š„šš, šš„šØš§š š„š¢š¦š¢š­ š¢š¬ {CLONE_LIMIT}GB.\nYour File/Folder size is {get_readable_file_size(size)}."
                return sendMessage(msg2, bot, message)
        if multi > 1:
            sleep(4)
            nextmsg = type('nextmsg', (object, ), {'chat_id': message.chat_id, 'message_id': message.reply_to_message.message_id + 1})
            nextmsg = sendMessage(args[0], bot, nextmsg)
            nextmsg.from_user.id = message.from_user.id
            multi -= 1
            sleep(4)
            Thread(target=_clone, args=(nextmsg, bot, multi)).start()
        if files <= 20:
            msg = sendMessage(f"Cloning: <code>{link}</code>", bot, message)
            result, button = gd.clone(link)
            deleteMessage(bot, msg)
        else:
            drive = GoogleDriveHelper(name)
            gid = ''.join(SystemRandom().choices(ascii_letters + digits, k=12))
            clone_status = CloneStatus(drive, size, message, gid)
            with download_dict_lock:
                download_dict[message.message_id] = clone_status
            sendStatusMessage(message, bot)
            result, button = drive.clone(link)
            with download_dict_lock:
                del download_dict[message.message_id]
                count = len(download_dict)
            try:
                if count == 0:
                    Interval[0].cancel()
                    del Interval[0]
                    delete_all_messages()
                else:
                    update_all_messages()
            except IndexError:
                pass
        cc = f'\nā°āš¬ šš² ā¢ {tag}\n\n'
        if button in ["cancelled", ""]:
            sendMessage(f"{tag} {result}", bot, message)
        else:
            if AUTO_DELETE_UPLOAD_MESSAGE_DURATION != -1:
                auto_delete_message = int(AUTO_DELETE_UPLOAD_MESSAGE_DURATION / 60)
                if message.chat.type == "private":
                    warnmsg = ""
                else:
                    autodel = secondsToText()
                    warnmsg = f" \n š§šµš¶š šŗš²ššš®š“š² šš¶š¹š¹ š®ššš¼ š±š²š¹š²šš²š± š¶š» {autodel}\n\n"
        if BOT_PM and message.chat.type != "private":
            pmwarn = f"š šµš®šš² šš²š»š š¹š¶š»šøš š¶š» š£š .\n"
        elif message.chat.type == "private":
            pmwarn = ""
        else:
            pmwarn = ""
        uploadmsg = sendMarkup(result + cc + pmwarn + warnmsg, bot, message, button)
        Thread(target=auto_delete_upload_message, args=(bot, message, uploadmsg).start()
        if MIRROR_LOGS:
            try:
                for i in MIRROR_LOGS:
                    bot.sendMessage(chat_id=i, text=result + cc, reply_markup=button, parse_mode=ParseMode.HTML)
            except Exception as e:
                LOGGER.warning(e)
            if BOT_PM and message.chat.type != "private":
                try:
                    LOGGER.info(message.chat.type)
                    bot.sendMessage(message.from_user.id, text=result + cc, reply_markup=button, parse_mode=ParseMode.HTML)
                except Exception as e:
                    LOGGER.warning(e)
                    return
            sendMarkup(result + cc, bot, message, button)
            LOGGER.info(f'Cloning Done: {name}')
    else:
        sendMessage('Send Gdrive or gdtot link along with command or by replying to the link by command', bot, message)

@new_thread
def cloneNode(update, context):
    _clone(update.message, context.bot)

clone_handler = CommandHandler(BotCommands.CloneCommand, cloneNode, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
dispatcher.add_handler(clone_handler)
