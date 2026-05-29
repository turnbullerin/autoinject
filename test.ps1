
deactivate
.\.venv14\Scripts\activate
echo ""
echo "###########"
echo "Python 3.14"
echo "###########"
echo ""
python -m pip -q -q -q install -r requirements/dev.txt
python -m coverage run --data-file=.coverage14 -m unittest
cd src
python -m mypy ../tests --check-untyped-defs
cd ../
deactivate
.\.venv13\Scripts\activate
echo ""
echo "###########"
echo "Python 3.13"
echo "###########"
echo ""
python -m pip -q -q -q install -r requirements/dev.txt
python -m coverage run --data-file=.coverage13 -m unittest
deactivate
.\.venv12\Scripts\activate
echo ""
echo "###########"
echo "Python 3.12"
echo "###########"
echo ""
python -m pip -q -q -q install -r requirements/dev.txt
python -m coverage run --data-file=.coverage12 -m unittest
deactivate
.\.venv11\Scripts\activate
echo ""
echo "###########"
echo "Python 3.11"
echo "###########"
echo ""
python -m pip -q -q -q install -r requirements/dev.txt
python -m coverage run --data-file=.coverage11 -m unittest
deactivate
.\.venv10\Scripts\activate
echo ""
echo "###########"
echo "Python 3.10"
echo "###########"
echo ""
python -m pip -q -q -q install -r requirements/dev.txt
python -m coverage run --data-file=.coverage10 -m unittest
deactivate
.\.venv9\Scripts\activate
echo ""
echo "###########"
echo "Python 3.9"
echo "###########"
echo ""
python -m pip -q -q -q install -r requirements/dev.txt
python -m coverage run --data-file=.coverage9 -m unittest
deactivate
.\.venv8\Scripts\activate
echo ""
echo "###########"
echo "Python 3.8"
echo "###########"
echo ""
python -m pip -q -q -q install -r requirements/dev.txt
python -m coverage run --data-file=.coverage8 -m unittest
deactivate
.\.venv14\Scripts\activate
python -m coverage combine --data-file=.coverage .coverage8 .coverage9 .coverage10 .coverage11 .coverage12 .coverage13 .coverage14
python -m coverage html --data-file=.coverage
