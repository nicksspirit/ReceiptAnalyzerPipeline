rm -rf ./aws_lambda/*
poetry build -f wheel
python -m pip install ./dist/anarcpt-0.1.0-py3-none-any.whl -t ./aws_lambda/
cp ./aws_lambda_fn.py ./aws_lambda/
zip aws_lambda_dist.zip ./aws_lambda/*