import React, { useState, useEffect } from 'react'
import {
    Table,
    Thead,
    Tbody,
    Tr,
    Th,
    Td,
    TableCaption,
    Flex,
    Spinner,
    Link,
    Button,
    HStack

} from "@chakra-ui/react"


import { getScanReportTableRows } from '../api/values'
import { downloadXLSXFile } from '../api/download'




const TablesTbl = () => {
    // get the value to use to query the fields endpoint from the page url
    const value = parseInt(new URLSearchParams(window.location.search).get("search"))
    const [values, setValues] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(undefined);
    const [loadingMessage, setLoadingMessage] = useState("");

    useEffect(() => {
        // get table on initial render
        getScanReportTableRows(value).then(table => {
            setValues(table)
            setLoading(false)
        })
    }, []);

    const download_scan_report = () => {
        downloadXLSXFile()
        
    };

    const download_data_dictionary = () => {
        window.download_data_dictionary()
    };

    if (loading) {
        //Render Loading State
        return (
            <div>
                <Flex padding="30px">
                    <Spinner />
                    <Flex marginLeft="10px">{loadingMessage ? loadingMessage : "Loading Tables"}</Flex>
                </Flex>
            </div>
        )
    }
    return (
        <div >
            <HStack my="10px">
            <Button variant="green" onClick={download_scan_report}>Download Scan Report File</Button>
            <Button variant="blue" isDisabled={window.hide_button} onClick={download_data_dictionary}>Download Data Dictionary File</Button>

            </HStack>

            <Table variant="striped" colorScheme="greyBasic">
                <TableCaption></TableCaption>
                <Thead>
                    <Tr>
                        <Th>Name</Th>
                        <Th>Person ID</Th>
                        <Th>Event Date</Th>
                        <Th>Edit</Th>
                    </Tr>
                </Thead>
                <Tbody>
                    {values.length > 0 ?
                        values.map((item, index) =>
                            <Tr key={index}>
                                <Td maxW={"200px"}><Link style={{ color: "#0000FF", }} href={"/fields/?search=" + item.id}>{item.name}</Link></Td>
                                <Td maxW={"200px"}>{item.person_id ? item.person_id.name : null} </Td>
                                <Td maxW={"200px"}>{item.date_event ? item.date_event.name : null}</Td>
                                <Td maxW={"200px"}><Link style={{ color: "#0000FF", }} href={"/tables/" + item.id + "/update/"}>Edit Table</Link></Td>
                            </Tr>

                        )
                        :
                        <Flex padding="30px">
                            <Flex marginLeft="10px">Nothing</Flex>
                        </Flex>
                    }
                </Tbody>
            </Table>
            <Link href={"/scanreports/"+value+"/mapping_rules/"}><Button variant="blue" my="10px">Go to Rules</Button></Link>
        </div>
    );
}

export default TablesTbl;