-- Single-node teaching CAS. Authority and roster KEYS share one hash tag.
-- ARGV: expected_version, complete next JSON, course_id, deleted(0/1).
-- Key types preflight avoids the demonstrated WRONGTYPE-after-write case.
local value_type = redis.call('TYPE', KEYS[1]).ok
local roster_type = redis.call('TYPE', KEYS[2]).ok
if value_type ~= 'none' and value_type ~= 'string' then return {'invalid_type'} end
if roster_type ~= 'none' and roster_type ~= 'set' then return {'invalid_type'} end
local current = redis.call('GET', KEYS[1])
local version = 0
if current then version = cjson.decode(current).version end
local expected = tonumber(ARGV[1])
if version ~= expected then return {'version_conflict', tostring(version)} end
local after = cjson.decode(ARGV[2])
if after.version ~= version + 1 then return {'invalid_next_version'} end
redis.call('SET', KEYS[1], ARGV[2])
if ARGV[4] == '1' then redis.call('SREM', KEYS[2], ARGV[3])
else redis.call('SADD', KEYS[2], ARGV[3]) end
return {'accepted', tostring(after.version)}
