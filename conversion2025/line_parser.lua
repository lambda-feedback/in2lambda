-- customer parser to parse input line by line except display math in a markdown file
local pandoc = require("pandoc")

function Reader(input, reader_opts)
    local lines = {}
    input = tostring(input)
    print(input)
    for line in (input .. "\n"):gmatch("(.-)\n") do
        table.insert(lines, line)
    end

    local blocks = {}
    local in_math = false
    local math_buffer = {}

    for _, line in ipairs(lines) do
        -- matches "$$"
        if line:match("%$%$") then
            -- end of display math
            if in_math then
                table.insert(math_buffer, line)
                local math_content = table.concat(math_buffer, "\n")
                table.insert(blocks, pandoc.Para{pandoc.Math("DisplayMath", math_content)})
                math_buffer = {}
                in_math = false
            
            -- start of display math
            else
                in_math = true
                math_buffer = {line}
            end
        
        -- middle of display math
        elseif in_math then
            table.insert(math_buffer, line)
        
        -- empty line
        elseif line:match("^%s*$") then
            -- skip empty lines

        -- a regular line
        else
            table.insert(blocks, pandoc.Para{pandoc.Str(line)})
        end
    end

    return pandoc.Pandoc(blocks)
end