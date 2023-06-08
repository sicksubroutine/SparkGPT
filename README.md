# SparkGPT
A relatively simple ChatGPT app using the ChatGPT API and LNBits API to accept Bitcoin over the Lightning Network for payment.

### Features:

* Improved design over previous "chat apps" I have created in the past using Javascript and AJAX so there is feedback when sending a message. Previously, the page wouldn't update until the ChatGPT API responded. 
* You can select from a series of preset prompts or you can input your own custom prompt. These custom prompts tend to work better than inputting your own prompt after the conversation has already started.
* A chat interface that includes the ability to easily delete individual messages, reset the chat entirely, and download the conversation history to a markdown file.
* Filename of the markdown file is ChatGPT generated based upon your initial message.
* Ability to have multiple concurrent chats going at the same time. Front page will have a small summary of the ongoing chat as well as the current prompt being used.
* Ability to change between GPT3.5 TURBO and GPT 4.
* Syntax highlighting with PrismJS for code blocks that might occur.
* Basic username and password authorization flow.
* Basic admin panel for user maintenance. 