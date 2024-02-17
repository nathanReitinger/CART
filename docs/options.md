# Options

`CART` accommodates several means of tweaking the reviewing process.  



## Flags 

| Flag | Use example                                | Description                                                  | Default          |
| ---- | ------------------------------------------ | ------------------------------------------------------------ | ---------------- |
| -c   | `-c user1 -c user2 -c user3`               | [required] creates accounts for users (three from example)   | user must supply |
| -r   | `-r 3`                                     | [optional] how many members should vote on each paper        | 2                |
| -p   | `-p 8080`                                  | [optional] what port will `CART` use                         | 8081             |
| -d   | `-d selected-crawdad-loved.ngrok-free.app` | [optional] will tell `CART` to use `ngrok` on a static domain provided by `ngrok` |                  |
| -n   | `-n 12345`                                 | [optional] pass in `ngrok` authToken to use ngrok server (allows the app to be accessible beyond localhost) |                  |
| -cf  | `-cf 100`                                  | [optional] confetti will spray on the 100th graded paper per member | 50               |

