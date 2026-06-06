input paragraph = 
"""
Idea Name: Context Fabric

Problem Statement: Build a context engine that sources timely data for commercial realtionsihps managers in the following dimensions.
    1. Balance Sheet, Income Statement, Cash Flow information sourced from Edgar 10ks and 10Qs. 
    2. Searches the internet for any releative recent news abou the company and classifies as good or bad. 
    3. Looks for industry comparison for the company and compares the target companies financial health against the industry averages by NIACS sector. 
    4. Looks at internal product saturation of existing company and compares product needs against actual transaction history to identify if new products are potentially a good fit for customer.
    5. Looks at a policy library to ensure we are aware of any compliance or policy related components for the company 
    6. Time dimension: this dimension is applied to all the other dimensions to display "freshness" in data.  It is critical we have timely data meeting our signal and appropriately weight the other five dimensions based upon the "freshness" of the data. 

Target Users: Commercial Relationsihp Managers

Key Features: A dashboard that gives fiscal health, comparison to industry, and builds a visual graph of how each of the dimensions above relate to the customer. 

Success Metrics: Product picker for the Relationsihp manager as well as the narrartive backed with financial metrics to support the conversation the Relationsihp manager will have with the customer. 

What your product is NOT: A toy demo. This is not for private companies. 