# Q2PM: An Interactive System for Query-to-Policy Mapping in Rural Australia
---
![Overview of the Q2PM System](figs/p2m.jpg)
_Figure: Climate Policy Navigator: Mapping Australia's Environmental Policy Data_



Q2PM is an interactive system that bridges the gap between rural communities and local government climate policies through automated query interpretation and policy matching. The system leverages slim language models to decompose natural queries into structured components and map them to relevant local government area (LGA) policy documents. Q2PM consists of three main components illustrated as following:

### Query Interpretation
  Query Interpretation to process natural query into following stcutred format. Given a natrual query $q$ `In Oakford, WA, in the Serpentine-Jarrahdale LGA, water scarcity and extreme heat are major challenges. What programs are in place to promote water efficiency and manage climate impacts in our region?"`, the $f$ extracted ($L, I , T)$:
 

```json
{
        "I": [
            "What climate resilience programs are in place in Serpentine-Jarrahdale LGA?",
            "How does Oakford manage water scarcity?",
            "What initiatives address extreme heat in WA?"
        ],
        "T": [
            "water efficiency",
            "climate resilience",
            "heat management"
        ],
        "L": {
            "query_suburb": "Oakford",
            "query_state": "WA",
            "query_lga": "Serpentine-Jarrahdale"
        }
```
### Policy Mapping
The collected policy data contains
- LGAs (362 entries)
- Suburbs (11,276 entries)
- Policy Documents (710 entries)
#### Suburb Schema
| Key                 | Value                                                                                               |
|---------------------|---------------------------------------------------------------------------------------------------|
| _id                | SAL51174                                                                                           |
| Area Code: 2016    | SSC51164                                                                                           |
| Census URL 2016    | [Census 2016](https://www.abs.gov.au/census/find-census-data/quickstats/2016/SSC51164)              |
| Census URL 2021    | [Census 2021](https://abs.gov.au/census/find-census-data/quickstats/2021/SAL51174)                 |
| sal_id             | SAL51174                                                                                           |
| Suburb             | Oakford                                                                                           |
| Postcode           | 6121                                                                                              |
| State              | WA                                                                                                |
| State Name         | Western Australia                                                                                 |
| Type               | Rural locality                                                                                   |
| LGA                | Serpentine-Jarrahdale                                                                             |
| Statistic Area     | Greater Perth                                                                                    |
| Elevation          | 22                                                                                                |
| Area (sqkm)        | 46.91                                                                                            |
| Latitude           | -32.20852                                                                                        |
| Longitude          | 115.92797                                                                                        |
| Timezone           | Australia/Perth                                                                                  |
| Government Level   | State suburbs                                                                                    |

---

####  LGA Schema
| Key                 | Value                                                                                              |
|---------------------|---------------------------------------------------------------------------------------------------|
| _id                | LGA57700                                                                                          |
| lga_id             | LGA57700                                                                                          |
| LGA                | Serpentine-Jarrahdale                                                                             |
| Government Level   | lga                                                                                               |
| LGA Type           | mixed                                                                                            |
| Government URL     | [Website](https://www.sjshire.wa.gov.au/)                                                        |
| Government Email   | info@sjshire.wa.gov.au                                                                           |
| State Name         | Western Australia                                                                                 |
| Census URL 2021    | [Census 2021](https://www.abs.gov.au/census/find-census-data/quickstats/2021/LGA57700)            |
| State              | WA                                                                                                |
| Number of Policies | 3                                                                                                 |

---

####  Policies Schema
| Policy ID    | Policy Name                                    | Policy URL                                                                                                   | Pages |
|--------------|------------------------------------------------|-------------------------------------------------------------------------------------------------------------|-------|
| LGA57700_1   | Strategy-and-Action-Plan-to-Climate-Change    | [Link](https://www.sjshire.wa.gov.au/Profiles/sj/Assets/ClientData/E22_7277__Attachment_2_-_2015_Strategy_and_Action_Plan_-_to_Climate_Change_Agenda_Report_Item.pdf) | 5     |
| LGA57700_2   | Council-Policy-2110-Energy-and-Water-Efficiency | [Link](https://www.sjshire.wa.gov.au/documents/144/council-policy-2110-energy-and-water-efficiency)         | 3     |
| LGA57700_3   | Council-Policy-2112-Street-Trees              | [Link](https://www.sjshire.wa.gov.au/documents/152/council-policy-2112-street-trees)                        | 10    |


### Action Devliery

- Generates comprehensive reports for [community analysis](output/community_analysis_text) and [policy analysis](output/community_analysis_text)
- Provides interactive map visualizations on our project website [https://next.counterinfodemic.org/](https://next.counterinfodemic.org/). 
- Automatically generates [feedback emails]((output/email_report_text)) to LGAs when information gaps are detected 

## FAQ

### Q: Where to download the Australia Policy dataset?
A: TBC

### 



## Acknowledgments
