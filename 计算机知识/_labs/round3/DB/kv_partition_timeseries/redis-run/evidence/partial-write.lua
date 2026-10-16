redis.call('SET',KEYS[1],'written-before-error'); redis.call('LPUSH',KEYS[2],'x'); return 'unreachable'
