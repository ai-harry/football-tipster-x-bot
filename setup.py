from setuptools import setup, find_packages

setup(
    name="football-tipster-x-bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "PySocks>=1.7.1",
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "openai>=1.3.7",
        "tweepy>=4.14.0",
        "python-multipart>=0.0.6",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="An automated football betting tips bot that posts on X (Twitter)",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/football-tipster-x-bot",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 