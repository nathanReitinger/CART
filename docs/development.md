# Development

[code-of-conduct]: CODE_OF_CONDUCT.md

[contributing]: CONTRIBUTING.md

Hi there! We're thrilled that you'd like to contribute to this project. 

Please note that this project is released with a [Contributor Code of Conduct][code-of-conduct]. By participating in this project you agree to abide by its terms. We also have a set of  [contributing guidelines][contributing], please look at them prior to working on this project.  



## Areas for improvement

| Area            | Comment                                                      |
| --------------- | ------------------------------------------------------------ |
| Mobile          | `CART` currently only works for desktop.                     |
| GUI             | Running `cart.py` may benefit from a GUI that allows users to select options instead of passing in flags. |
| Login           | `CART` assumes users are honest and therefore does not require login passwords or other security-facing features. Some teams may prefer tooling that helps enforce access control, like logins with a password. |
| Post-processing | `CART` would benefit from a task that compiles all votes cast into a single csv file; currently, `CART` stores papers (as `.csv` files) with votes cast per user, but does not aggregate all of these into a single file for completion post-processing. |



## Testing 

Testing scripts are found in the `/testing` folder. The `test.py` program

```bash
python3 test.py
```

will do the following:

- use Selenium for testing
- setup `CART` by moving test abstracts into the right folder
  - abstracts will be moved into the `abstracts/-testing/` folder (and cleaned up when `test.py` exits) 
- use a "small" set of abstracts
  - login as a provided user and vote on 5 abstracts (`number_to_vote` argument)
    - checking login 
    - checking vote casting
    - checking "done" or completed on all abstracts voted on
    - teardown to reset abstracts
- use a "big" set of abstracts 
  - login as a provided user and vote on 50 abstracts (`number_to_vote` argument)
    - checking login 
    - checking vote casting
    - checking "done" or completed on all abstracts voted on
    - teardown to reset abstracts
- print results of tests to terminal 

