from setuptools import setup

setup(
   name='marketing_attribution_models',
   version='1.0',
   description='Metodos de atribuicao de midia',
   author='Andre Tocci',
   author_email='andre.tocci@dp6.com.br',
   packages=['marketing_attribution_models'],  #same as name
   install_requires=['numpy', 'pandas','matplotlib', 'seaborn', ], #external packages as dependencies
)
