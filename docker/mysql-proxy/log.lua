local log_file = os.getenv("LOG_FILE")

local fh = io.open(log_file, "a+")

function read_query( packet )
    if string.byte(packet) == proxy.COM_QUERY then
        local query = string.sub(packet, 2)
        fh:write( string.format("%s %6d -- %s \n",
            os.date('%Y-%m-%d %H:%M:%S'),
            proxy.connection.server["thread_id"],
            query))
        fh:flush()
    end
end
