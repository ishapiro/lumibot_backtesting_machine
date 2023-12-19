Lumibot Iron Condor Benchmarking Experiment

# This project is not ready for use.  It is a work in process and does not work correctly.

This is my first experiment using the Lumibot framework to build a robust Iron Condor Backtesting environment.  Once completed
I will ensure the reliability of the code by comparing results to alternative commercially available backtesting environments.

## Background

    Iron Condor Structure
    
    call log position
    call short position
    call short_strike_boundary
    
    Initial Stock Position
    
    put short_strike_boundary
    put short position
    put long posittion


The goal of the effort is to create a flexible Iron Condor backtesting solution easily modified by updating
parameters.   In future efforts these parameters will be exposed via web front end.

## Development

I have used MacOS for development with the following setup:

```
brew install python@3.11
```

Then open up vscode, and from the terminal, create an environment for your development.

```
python3 -m venv lumibot-env
source lumibot-env/bin/activate
```

Create a new directory at the next level down.  You do not want the env at the same level as the code because this will cause an issue with git.

If you are inside of the code directory, activate the env with:

```
../lumibot-env/bin/activate
```

Open the new directory in a terminal and run vscode as follows:

```
code .   
```

In VSCode, invoke the command prompt with cmd/shift/p and then type Python: Select Interpreter.  Make sure the Python interpreter is set
to the lumibot env.

The code is extensively commented.

To run, you need to create a file credentials.py containing your Poloycom API key:

```
POLYGON_CONFIG = {
    # Put your own Polygon key here:
    "API_KEY": "hjkhkjhjkhkjhkjhkjhkjhhk",
}
```



