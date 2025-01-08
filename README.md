## d/place
d/place is a recreation of r/place in discord. This is my first discord bot so it might have errors and it can be bad.

## Setup

1. Create a file called `token.json`, and then add to it this:
```
{
    "token": "YOUR BOT TOKEN"
}
```
2. ``` pip install -r requirements.txt ```
3. ``` python main.py ```

## Commands

- ``` /dplace x y color ```: Places a pixel on the canvas at the specified `x` and `y` coordinates. The color can be specified in three formats:
  - Hex color
  - RGB
  - Color names: `red`, `green`, `blue`, `yellow`, `cyan`, `magenta`, `white`, `black`, `orange`, `purple`, `pink`, `gray` or `gold`

- ``` /info ```: Displays the time left and the leaderboard

- ``` /canvas ```: Sends an image of the current canvas
