# Tito Ticketing API wrapper

Important: run with ONE worker only!
```
uvicorn main:app --port 8080 --host "0.0.0.0" 
```

It takes about 30 sec to launch, data is loaded and process from Tito

```
export IMAGE_NAME=pyconde_tito_2547
AWS_REGION=eu-central-1
export IMAGE_REPO=718419346402.dkr.ecr.eu-central-1.amazonaws.com
export IMAGE_URL=$IMAGE_REPO/pyconde_tito_2547

```


```
export VERSION=v5

docker buildx build --platform linux/amd64 -t pyconde_tito .
docker tag $IMAGE_NAME $IMAGE_URL:$VERSION


```
conda activate tito_api_wrapper_dev
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $IMAGE_URL:latest
```