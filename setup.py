from setuptools import setup, find_packages

setup(
    name='flask-request-parser',
    version='1.0.0',
    packages=find_packages(exclude=['tests', 'venv']),
    install_requires=['Flask'],
    url='https://github.com/Aokigahara23/flask-request-parser',
    license='',
    author='forest23',
    author_email='aokigahara23@gmail.com',
    description='My vision on flask request parser'
)
