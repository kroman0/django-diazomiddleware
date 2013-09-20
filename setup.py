from setuptools import setup, find_packages

VERSION = '0.1'

REQUIREMENTS = (
    'setuptools>=0.6c11',
    'django',  # ???
    'diazo>=1.0.3',
    'webob',
    'repoze.xmliter',
)
TEST_REQUIREMENTS = (
)


setup(
    name="django_diazomiddleware",
    version=VERSION,
    keywords='django diazo middleware xslt python',
    author='Roman Kozlovskyi',
    author_email='krzroman@gmail.com',
    description="Integrate Diazo in Django using Django middleware mechanism.",
    url="https://github.com/kroman0/django-diazomiddleware",
    packages=find_packages(),
    include_package_data=True,
    install_requires=REQUIREMENTS,
    tests_require=TEST_REQUIREMENTS,
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
