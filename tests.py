import unittest

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=3)
    suite = unittest.TestLoader().discover('.', pattern="test_*.py")
    runner.run(suite)
