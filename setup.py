from setuptools import setup, find_packages

setup(
    name="gcp_inventory_final",
    version="0.1.0",
    description="GCP infrastructure inventory to Excel and upload to GCS",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.3",
        "openpyxl>=3.0",
        "google-cloud-asset>=2.8.0",
        "google-cloud-storage>=2.7.0",
    ],
    entry_points={
        "console_scripts": [
            "gcp-inventory-final = gcp_inventory.inventory:main",
        ]
    },
)
