import json
import os
import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from restcli import MemMachineRestClient
from process_chat_history import locomo_count_conversations
from process_chat_history import load_locomo


class MigrationHack:
    def __init__(self, base_url="http://127.0.0.1:8080",
                 user_session_file="user_session.json",
                 locomo_file="data/locomo10.json",
                 extract_dir="extracted"):
        self.user_session_file = user_session_file
        with open(self.user_session_file, "r") as f:
            self.user_session = json.load(f)
        self.base_url = base_url
        self.client = MemMachineRestClient(base_url=self.base_url,
                                           session=self.user_session,
                                           verbose=False)
        self.locomo_file = locomo_file
        self.extract_dir = extract_dir
        # list of messages in conversations loaded from file
        self.num_conversations = 0
        self.messages = {}  # key: conversation id, value: list of messages

    def load(self):
        total_messages = 0
        if self.locomo_file is not None:
            print(f"-> loading locomo file {self.locomo_file}")
            print(f"-> counting conversations...")
            conv_count = locomo_count_conversations(self.locomo_file, verbose=False)
            print(f"-> loaded {conv_count} conversations from locomo file")
            self.num_conversations = conv_count
            for conv_id in range(1, self.num_conversations + 1):
                print(f"---> loading messages from conversation {conv_id}...")
                messages = load_locomo(self.locomo_file,
                                       start_time=0, conv_num=conv_id, max_messages=0, verbose=False)
                print(f"---> loaded {len(messages)} messages from conversation {conv_id}")
                total_messages += len(messages)
                self.messages[conv_id] = messages
        print(f"Loaded {total_messages} messages from locomo file")
        # write into extract_dir
        os.makedirs(self.extract_dir, exist_ok=True)
        # Format the extracted file name with timestamp suffix
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # Extract the base filename from the locomo file path
        locomo_name = os.path.splitext(os.path.basename(self.locomo_file))[0]
        # Create the extract file name with timestamp
        extract_file_prefix = f"{locomo_name}_extracted_{timestamp}"
        for conv_id in self.messages:
            extract_file = f"{extract_file_prefix}_conv_{conv_id}.txt"
            extract_file = os.path.join(self.extract_dir, extract_file)
            with open(extract_file, "w") as f:
                # Write each message line by line to the extract file
                for message in self.messages[conv_id]:
                    f.write(message + "\n")

    def _process_conversation(self, conv_id, messages):
        """Process a single conversation with its own progress bar"""
        # Create a progress bar for this conversation
        pos = conv_id - 1
        msg_pbar = tqdm(messages, desc=f"Conv {conv_id}", unit="msg", position=pos, leave=True)
        for message in msg_pbar:
            # TODO: insert messages into episodic memory
            self.client.post_episodic_memory(message, session_id=f"conversation_{conv_id}")

        msg_pbar.close()
        return conv_id, len(messages)

    def insert_memories(self):
        print(f"--- Inserting memories starts")

        # Process conversations concurrently using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(self.num_conversations, 5)) as executor:
            # Submit all conversation processing tasks
            future_to_conv = {
                executor.submit(self._process_conversation, conv_id, messages): conv_id
                for conv_id, messages in self.messages.items()
            }

            # Create a progress bar for completed conversations
            completed_pbar = tqdm(total=len(self.messages), desc="Completed conversations", unit="conv")

            # Process completed tasks
            for future in as_completed(future_to_conv):
                conv_id, msg_count = future.result()
                completed_pbar.set_description(f"Completed conv {conv_id} ({msg_count} msgs)")
                completed_pbar.update(1)

            completed_pbar.close()

        print(f"--- Inserting memories done")

    def migrate(self):
        print(f"== Loading starts")
        self.load()
        print(f"== Loading done")
        print(f"== Migration starts")
        self.insert_memories()
        print(f"== Migration done")


if __name__ == "__main__":
    migration_hack = MigrationHack(base_url="http://52.15.149.39:8080",
                                   user_session_file="user_session.json",
                                   locomo_file="data/locomo10.json")
    migration_hack.migrate()
    print(f"== All completed successfully")
