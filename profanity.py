from guildedRequest import muteUser

PROFANITY_TRIE = {}
PROFANITY = None
CONFIG = None


def setupProfanity(config, profanity):
  global CONFIG, PROFANITY, PROFANITY_TRIE
  CONFIG = config
  PROFANITY = profanity
  buildProfanityTrie(PROFANITY)

def buildProfanityTrie(PROFANITY):
  global PROFANITY_TRIE
  for word in PROFANITY:
    letters = word.lower()
    letter = 0
    ptr = PROFANITY_TRIE
    if len(letters) == 0:
      continue

    while True:
      if letters[letter] not in ptr:
        ptr[letters[letter]] = {}
      ptr = ptr[letters[letter]]
      letter += 1
      if len(letters) == letter:
        ptr['profanity'] = PROFANITY[word]
        break


def checkForProfanity(content):
  global PROFANITY_TRIE
  content = content.lower()\
      .replace('1', 'i')\
      .replace('!', 'i')\
      .replace('3', 'e')\
      .replace('0', 'o')\
      .replace('4', 'a')
  index = 0
  profanities = []
  prev_char = ''
  EOS = len(content)
  while index < EOS:
    if content[index] in PROFANITY_TRIE:
      ptr = PROFANITY_TRIE[content[index]]
      sub_index = index + 1
      while sub_index < EOS:
        if content[sub_index] not in ptr:
          if content[sub_index].isalpha() and content[sub_index] != prev_char:
            break
          else:
            sub_index += 1
            continue
        ptr = ptr[content[sub_index]]
        prev_char = content[sub_index]
        if 'profanity' in ptr:
          if ptr['profanity']['must_be_start_of_word']:
            if index != 0 and content[index-1].isalpha():
              break
          profanities.append({
              'profanity': ptr['profanity'],
              'start': index,
              'end': sub_index+1
          })
          index = sub_index
          break
        sub_index += 1
    index += 1

  if len(profanities) > 0:
    return profanities
  return None


async def handleProfanity(message, profanity):
  newContent = message.content
  notify = False

  for p in profanity:
    if p['profanity']['how_to_handle'] == 'Censor word':
      newContent = newContent[0:p['start']+1] + \
          ''.join(['•' for i in range(p['start']+1, p['end'])]) + \
          newContent[p['end']:]
    elif p['profanity']['how_to_handle'] == 'Instant ban':
      await message.author.ban(reason=f'Fedposting or unallowed language')
      await message.delete()
      return
    elif p['profanity']['how_to_handle'] == 'Leave and notify moderator':
      notify = True
    elif p['profanity']['how_to_handle'] == 'Delete and mute user':
      await message.delete()
      await muteUser(message.author)
      return
    elif p['profanity']['how_to_handle'] == 'Swap word with another':
      newContent = newContent[0:p['start']] + p['profanity']['word_to_swap'] + \
          newContent[p['end']:]

  #todo: notify user
  await message.reply(message.author.name + ': ' + newContent)
  await message.reply(CONFIG['Watch_The_Profanity'], private=True)
  return await message.delete()
