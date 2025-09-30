#!/usr/bin/python3

import os
import sys
import argparse
import re
import json
import datetime


def timestamp_compare(ts1, ts2):
    ts1 = timestamp_ms_to_sec(ts1)
    ts2 = timestamp_ms_to_sec(ts2)
    if ts1 < ts2:
        return(-1)
    if ts1 > ts2:
        return(1)
    return(0)


def timestamp_ms_to_sec(ts):
    if isinstance(ts, float):
        ts = int(ts)
    if ts > 9999999999:
        ts = int(ts / 1000)
    return(ts)


def timestamp_to_obj(ts):
    ts = timestamp_ms_to_sec(ts)
    t_obj = datetime.datetime.fromtimestamp(ts)
    return(t_obj)


def load_locomo(infile, start_time=None, conv_num=None, max_messages=None, verbose=False):
    if not start_time:
        start_time = 0
    if not conv_num:
        conv_num = 0
    if not max_messages:
        max_messages = 0
    lines = []
    if verbose:
        print(f'll: start_time={start_time} conv_num={conv_num} max_messages={max_messages}', file=sys.stderr)
    if verbose:
        print(f'loading locomo input file {infile}', file=sys.stderr)
    with open(infile) as fp:
        data = json.load(fp)
    # loop to load every session
    conv_count = 0
    msg_count = 0
    section_count = 0
    done = False
    while not done:
        for section in data:
            section_count += 1
            if verbose:
                print(f'look for next conversation section {section_count}', file=sys.stderr)
                print(f'keys={list(section.keys())}', file=sys.stderr)
            if 'conversation' in section:
                conversation = section['conversation']
                conv_count += 1
                if conv_num and conv_count != conv_num:
                    # user asked to do one specific conversation
                    continue
                if verbose:
                    print(f'loading conversation {conv_count}', file=sys.stderr)
                for num in range(1, 9999):
                    session_name = f'session_{num}'
                    session_date_name = f'session_{num}_date_time'
                    if session_name not in conversation:
                        # processed all of the sessions in this conversation
                        if verbose:
                            print(f'finished conversation {conv_count} (1)', file=sys.stderr)
                        break
                    if verbose:
                        print(f'loading conversation {conv_count} session {num}', file=sys.stderr)
                    messages = conversation[session_name]
                    session_date_str = ''
                    session_date_obj = None
                    if not session_date_obj:
                        try:
                            session_date_str = conversation[session_date_name]
                            session_date_obj = datetime.datetime.strptime(session_date_str, '%I:%M %p on %d %b, %Y')
                        except Exception:
                            pass
                    if not session_date_obj:
                        try:
                            session_date_str = conversation[session_date_name]
                            session_date_obj = datetime.datetime.strptime(session_date_str, '%I:%M %p on %d %B, %Y')
                        except Exception:
                            pass
                    try:
                        session_time = session_date_obj.timestamp()
                        if start_time:
                            if timestamp_compare(start_time, session_time) > 0:
                                if verbose:
                                    print(f'skipping old conversation {conv_count} session {num} time={session_time}', file=sys.stderr)
                                break
                    except Exception:
                        if verbose:
                            print(f'ERROR: cannot read timestamp of conversation {conv_count} session {num} date={session_date_str}', file=sys.stderr)
                    for message in messages:
                        if 'text' in message:
                            lines.append(message['text'])
                            msg_count += 1
                            if max_messages and msg_count >= max_messages:
                                # user asked to do this many messages only
                                if verbose:
                                    print(f'processed max messages={msg_count}', file=sys.stderr)
                                done = True
                                break
                    if done:
                        break
                if verbose:
                    print(f'finished conversation {conv_count} sessions={num}', file=sys.stderr)
            if verbose:
                print(f'finished conversation {conv_count} (2)', file=sys.stderr)
            if done:
                break
        if verbose:
            print(f'loaded all sections={section_count}', file=sys.stderr)
        done = True
    return(lines)


def get_args():
    parser = argparse.ArgumentParser(description='Process chat history', add_help=False)
    parser.add_argument('-h', '--help', action='store_true', help='print usage')
    parser.add_argument('-v', '--verbose', action='store_true', help='print debug info if available')
    parser.add_argument('--src', action='store', default='locomo', help='openai|locomo, default=locomo')
    parser.add_argument('-i', '--infile', action='store', help='input chat history')
    parser.add_argument('-o', '--outfile', action='store', help='output parsed chat')
    parser.add_argument('-t', '--start_time', action='store', help='only read messages after this time either YYYY-MM-DDTHH:MM:SS or secs since epoch')
    parser.add_argument('-n', '--max_messages', action='store', type=int, default=0, help='only read this many messages')
    parser.add_argument('--locomo_conversation', action='store', type=int, default=0, help='load only this conversation')
    # parser.add_argument('--summarize_every', action='store', type=int, default=0, help='summarize before storing into memmachine, default is 0')
    args = parser.parse_args()
    if args.help:
        usage(args)
        sys.exit(0)
    if not args.infile:
        print(f'ERROR: must specify --infile', file=sys.stderr)
        sys.exit(1)
    if args.start_time:
        ts = 0
        try:
            # time in int
            ts = int(args.start_time)
        except Exception:
            pass
        if not ts:
            try:
                # time is str
                time_obj = datetime.datetime.strptime(args.start_time, '%Y-%m-%dT%H:%M:%S')
                ts = time_obj.timestamp()
            except Exception:
                pass
        args.start_time = ts
    return(args)


def usage(args):
    prog = os.path.basename(sys.argv[0])
    # print(f'Usage: {prog} [--src <src>] [--infile <chat_history>] [--outfile <parsed_chat>] [--summarize_every <n_messages>] [--start_time <timestamp>')
    print(f'Usage: {prog} [--src <src>] --infile <chat_history> [--outfile <parsed_chat>] [--start_time <timestamp> [--num_messages <n>] [--locomo_conversation <n>]')
    print(f'')
    print(f'src: input file format, either locomo or openai')
    print(f'infile: input filename')
    print(f'outfile: output filename, default is stdout')
    print(f'start_time: read message after this time')
    print(f'    either YYYY-MM-DDTHH:MM:SS or secs since epoch')
    print(f'num_messages: read only this many messages')
    print(f'locomo_conversation: if input is locomo, load only this conversation')
    print(f'')


if __name__ == '__main__':
    args = get_args()
    args.src = args.src.lower()
    if args.src == 'locomo':
        lines = load_locomo(args.infile, args.start_time, args.locomo_conversation, args.max_messages, args.verbose)
    if args.outfile:
        fp = open(args.outfile, 'w')
    else:
        fp = sys.stdout
    for line in lines:
        line = line.strip()
        line = re.sub(r'\\n', ' ', line)
        line = re.sub(r'\n', ' ', line)
        print(f'{line}', file=fp)
