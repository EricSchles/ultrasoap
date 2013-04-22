#!/usr/bin/env python
import logging
import sys

from driver import get_neustar


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('suds.client').setLevel(logging.DEBUG)

    client = get_neustar()
    client.rollback_transaction(sys.argv[1])


if __name__ == '__main__':
    main()
