# udns_ssearch

This script fetches information about UltraDNS subaccounts, zones, and pools. By default, this will pull each subaccount from the given primary account and search every zone in the account to see if any pool records are present. The output includes the subaccount name, zone name, pool name, and pool type. This can, of course, be refactored to iterate through other APIs within the subaccounts. It supports output in both JSON and CSV formats.

## Requirements

- Python 3
- Required Libraries:
  - `requests`
  - `tqdm`

You can install these required libraries using the `requirements.txt` file located in the root directory:

```bash
pip install -r requirements.txt
```

## Usage

The script can authenticate using either username and password or directly by providing an authentication token. The results can be either printed to the terminal or saved to an output file.

### Arguments

- `--username`: Username for authentication.
- `--password`: Password for authentication.
- `--token`: Directly pass the Bearer token.
- `--output-file`: Provide the name of the output file. If this argument isn't passed, the results will be printed to the terminal.
- `--format`: Specify the output format. Available choices are 'json' and 'csv'. Default is 'json'.

### Examples

1. Using username and password with JSON output printed to terminal:
   ```bash
   python ssearch.py --username <YOUR_USERNAME> --password <YOUR_PASSWORD>
   ```

2. Using token with JSON output saved to a file:
   ```bash
   python ssearch.py --token <YOUR_TOKEN> --output-file ~/Desktop/results.json
   ```

3. Using username and password with CSV output saved to a file:
   ```bash
   python ssearch.py --username <YOUR_USERNAME> --password <YOUR_PASSWORD> --format csv --output-file ~/Desktop/results.csv
   ```

## License

[MIT License](LICENSE)