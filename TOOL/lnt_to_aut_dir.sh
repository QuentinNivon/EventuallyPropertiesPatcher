#!/bin/bash
EXIT_SUCCESS=0
DAUT_ALREADY_EXISTS=1
BCG_ALREADY_EXISTS=2
BCG_GENERATION_FAILED=3
DAUT_GENERATION_FAILED=4
BAD_USAGE=5

if [ $# -eq 2 ]
then
    Directory=$1
    FileName=$2
    if [ -f "$Directory/$FileName.daut" ]
    then
        echo "Error: $FileName.daut already exists in $Directory."
        exit $DAUT_ALREADY_EXISTS
    else
        if [ -f "$Directory/$FileName.bcg" ]
        then
            echo "Error: $FileName.bcg (transition file) already exists in $Directory."
            exit $BCG_ALREADY_EXISTS
        else
            lnt.open "$Directory/$FileName".lnt generator "$Directory/$FileName".bcg
            BcgGenerated=$?

            if [ $BcgGenerated -eq 0 ]
            then
                bcg_open "$Directory/$FileName".bcg reductor -weaktrace "$Directory/$FileName"_weaktraced.bcg
                WeaktraceGenerated=$?

                bcg_io "$Directory/$FileName"_weaktraced.bcg "$Directory/$FileName"_weaktraced.aut
                AutGenerated=$?
                
                mv "$Directory/$FileName"_weaktraced.aut "$Directory/$FileName".daut
               
                if [ $AutGenerated -eq 0 ] && [ $WeaktraceGenerated -eq 0 ]
                then
                    rm "$Directory/$FileName".bcg -f > /dev/null
                    rm "$Directory/$FileName"_weaktraced.bcg > /dev/null
                    echo "Conversion completed."
                else
                    rm "$Directory/$FileName".bcg -f > /dev/null
                    rm "$Directory/$FileName".daut -f > /dev/null
                    rm "$Directory/$FileName"_weaktraced.bcg > /dev/null
                    echo "Error: Failed to generate $FileName.daut"
                    exit $DAUT_GENERATION_FAILED
                fi
            else
                rm "$Directory/$FileName".bcg -f > /dev/null
                echo "Error: Failed to generate $FileName.bcg"
                exit $BCG_GENERATION_FAILED
            fi
        fi
    fi

    rm -f -- *.o > /dev/null
    rm -f -- *.err > /dev/null
    rm -f reductor > /dev/null
    rm -f generator > /dev/null
    rm -f prodcpl.prd > /dev/null

    rm -f "$Directory"/*.o > /dev/null
    rm -f "$Directory"/*.err > /dev/null
    rm -f "$Directory"/reductor > /dev/null
    rm -f "$Directory"/generator > /dev/null
    rm -f "$Directory"/prodcpl.prd > /dev/null

    exit $EXIT_SUCCESS
else
    echo "Usage: ./lnt_to_aut.sh <directory> <lnt_filename_without_extension>"
    exit $BAD_USAGE
fi
