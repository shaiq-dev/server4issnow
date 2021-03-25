from typing import Optional
import asyncio
import requests
import json
import concurrent.futures
from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import uuid

# Utility functions


def get_current_data_stamp() -> dict:
    '''
    Fetches ISS pose data from an api and returns the data in
    json format
    '''

    api = 'https://api.wheretheiss.at/v1/satellites/25544'
    data = requests.get(api)
    return data.json()


def is_iss_above_water(latitude: float, longitude: float) -> bool:
    '''
    Checkes if the ISS is currently above water or not
    '''
    key = '7ae291dd733f4f4cb52d87f2eda625c4'
    api = f'https://api.opencagedata.com/geocode/v1/json?q={latitude}+{longitude}&key={key}'
    response = requests.get(api).json()
    is_water = response['results'][0]['components']['_category']
    return is_water == 'natural/water'


# Main FstAPI App Instance
app = FastAPI()

# To allow cross origin request to the app
# we need to add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get('/api/pose')
async def pose():
    pose = get_current_data_stamp()
    pose['above_water'] = is_iss_above_water(
        pose['latitude'], pose['longitude'])
    return JSONResponse(content=pose)


@app.get('/api/stream')
async def stream(request: Request, dealy: Optional[int] = 1):
    async def generator() -> dict:

        __sep__ = '\n\n'

        with concurrent.futures.ThreadPoolExecutor() as executor:
            while True:

                if await request.is_disconnected():
                    break

                future = executor.submit(get_current_data_stamp)
                result = json.dumps(future.result())

                yield {
                    "id": uuid.uuid4().hex,
                    "retry": 1500,
                    "data": result
                }

                await asyncio.sleep(dealy)

    return EventSourceResponse(generator())


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", debug=False)
