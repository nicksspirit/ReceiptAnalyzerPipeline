# Receipt Analyzer Pipeline

### Steps to Build AWS Lambda for Deployment

```bash
rm -rf ./aws_lambda/*
poetry build -f wheel
python3 -m pip install .\dist\anarcpt-0.1.0-py3-none-any.whl -t ./aws_lambda/
cp .\aws_lambda_fn.py .\aws_lambda\
## Windows
7z a aws_lambda_dist.zip ./aws_lambda/*
```



```js
jamespath query

ExpenseDocuments[].SummaryFields[].[{TypeText: Type.Text, TypeConfidence: Type.Confidence, ValueText: ValueDetection.Text, ValueConfidence: ValueDetection.Confidence}][]
```



## External Dependencies

- ImageMagick
- AWSCLI (AWS Credentials)